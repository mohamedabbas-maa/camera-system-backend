# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from database import SessionLocal, Base, engine
from models import Users, Cameras
from auth import hash_password, verify_password, create_access_token, get_current_user
from stream import router as stream_router

# ----------------- Database Setup -----------------
Base.metadata.create_all(bind=engine)

def getdb():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- Schemas -----------------
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    token: str | None = None
    message: str | None = None

class CameraIn(BaseModel):
    name: str
    ip: str
    username: str
    password: str
    location: str | None = None
    enabled: bool = True
    stream_type: str = "rtsp"
    rtsp_link: str | None = None

class CameraOut(BaseModel):
    id: int
    name: str
    ip: str
    username: str
    password: str
    location: str | None = None
    enabled: bool
    stream_type: str
    rtsp_link: str | None = None
    model_config = ConfigDict(from_attributes=True)

# ----------------- Lifespan -----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        existing = db.query(Users).filter(Users.username=="admin").first()
        if not existing:
            user = Users(username="admin", password_hash=hash_password("1234"), role="admin", is_active=True)
            db.add(user)
            db.commit()
            print("Test user created: admin / 1234")
    finally:
        db.close()
    yield

# ----------------- App -----------------
app = FastAPI(title="Camera System API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")

@app.get("/")
async def root():
    return FileResponse("../frontend/dashboard.html")

# ----------------- Auth -----------------
@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(getdb)):
    user = db.query(Users).filter(Users.username==data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        return LoginResponse(status="error", message="Invalid username or password")
    token = create_access_token({"sub": user.username})
    return LoginResponse(status="success", token=token)

@app.get("/protected")
def protectedroute(currentuser: str = Depends(get_current_user)):
    return {"status":"success","user":currentuser}

# ----------------- Camera Endpoints -----------------
@app.post("/cams")
def add_cam(cam: CameraIn, db: Session = Depends(getdb), currentuser: str = Depends(get_current_user)):
    obj = Cameras(**cam.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"status":"success","user":currentuser,"camera_id":obj.id}

@app.get("/cams")
def get_cams(db: Session = Depends(getdb), currentuser: str = Depends(get_current_user)):
    cams = db.query(Cameras).all()
    return {"status":"success","user":currentuser,"cams":[CameraOut.model_validate(c).model_dump() for c in cams]}

@app.delete("/cams/{camera_id}")
def delete_cam(camera_id: int, db: Session = Depends(getdb), currentuser: str = Depends(get_current_user)):
    obj = db.query(Cameras).filter(Cameras.id==camera_id).first()
    if not obj:
        return {"status":"error","message":"Camera not found"}
    db.delete(obj)
    db.commit()
    return {"status":"success","user":currentuser,"deleted_id":camera_id}

# ----------------- Include streaming router -----------------
app.include_router(stream_router)
