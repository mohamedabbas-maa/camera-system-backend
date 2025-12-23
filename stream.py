import cv2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# RTSP URLs for the CCTV cameras
CAM1 = "rtsp://admin:Retail%40dmin010@192.168.100.151:554/cam/realmonitor?channel=1&subtype=1"
CAM2 = "rtsp://admin:Retail%40dmin010@192.168.100.152:554/cam/realmonitor?channel=1&subtype=1"

app = FastAPI(title="Camera Stream Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def mjpeg_generator(rtsp_url: str):
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        # If camera is unreachable, keep the connection open (empty frames)
        while True:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n"

    while True:
        success, frame = cap.read()
        if not success:
            break

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        jpg_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
        )

    cap.release()

@app.get("/stream/cam1")
def stream_cam1():
    return StreamingResponse(
        mjpeg_generator(CAM1),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@app.get("/stream/cam2")
def stream_cam2():
    return StreamingResponse(
        mjpeg_generator(CAM2),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
