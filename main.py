from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from contextlib import asynccontextmanager

from database import SessionLocal, Base, engine
from models import User, Camera
from auth import hashpassword, verifypassword, createaccesstoken, getcurrentuser


# Create tables at startup (IMPORTANT: models must be imported before this)
Base.metadata.create_all(bind=engine)


# DB dependency
def getdb():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    status: str
    token: str | None = None
    message: str | None = None


class CameraIn(BaseModel):
    name: str
    location: str | None = None
    stream_url: str
    enabled: bool = True


class CameraOut(BaseModel):
    id: int
    name: str
    location: str | None = None
    stream_url: str
    enabled: bool

    class Config:
        from_attributes = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed a test admin user if missing
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            user = User(
                username="admin",
                password_hash=hashpassword("1234"),
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            print("Test user created: admin / 1234")
    finally:
        db.close()

    yield

    print("Shutting down...")


app = FastAPI(title="Camera System API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(getdb)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verifypassword(data.password, user.password_hash):
        return LoginResponse(status="error", message="Invalid username or password")

    token = createaccesstoken({"sub": user.username})
    return LoginResponse(status="success", token=token)


@app.get("/protected")
def protectedroute(currentuser: str = Depends(getcurrentuser)):
    return {"status": "success", "user": currentuser}


# Create camera (store in DB)
@app.post("/cams")
def add_cam(
    cam: CameraIn,
    db: Session = Depends(getdb),
    currentuser: str = Depends(getcurrentuser),
):
    obj = Camera(**cam.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"status": "success", "user": currentuser, "camera_id": obj.id}


# List cameras (read from DB)
@app.get("/cams")
def get_cams(db: Session = Depends(getdb), currentuser: str = Depends(getcurrentuser)):
    cams = db.query(Camera).all()
    return {
        "status": "success",
        "user": currentuser,
        "cams": [CameraOut.model_validate(c).model_dump() for c in cams],
    }


# Optional: delete camera
@app.delete("/cams/{camera_id}")
def delete_cam(
    camera_id: int,
    db: Session = Depends(getdb),
    currentuser: str = Depends(getcurrentuser),
):
    obj = db.query(Camera).filter(Camera.id == camera_id).first()
    if not obj:
        return {"status": "error", "message": "Camera not found"}

    db.delete(obj)
    db.commit()
    return {"status": "success", "user": currentuser, "deleted_id": camera_id}
