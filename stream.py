# stream.py
import cv2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Cameras

router = APIRouter()

def mjpeg_generator(rtsp_url: str):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        while True:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n"

    while True:
        success, frame = cap.read()
        if not success:
            break
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
    cap.release()

def build_rtsp_from_camera(cam: Cameras) -> str:
    if getattr(cam, "rtsp_link", None):
        return cam.rtsp_link
    return f"rtsp://{cam.username}:{cam.password}@{cam.ip}:554/cam/realmonitor?channel=1&subtype=1"

@router.get("/stream/{camera_id}")
def stream_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Cameras).filter(Cameras.id == camera_id, Cameras.enabled==True).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found or disabled")
    rtsp_url = build_rtsp_from_camera(cam)
    return StreamingResponse(
        mjpeg_generator(rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
