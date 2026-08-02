from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import test_connection
from routes.attendance import router
from routes.attendance import router as attendance_router
from routes.liveness import router as liveness_router



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://attendance-frontend-rose.vercel.app","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_connection()
app.include_router(router, prefix="/api", tags=["attendance"])
app.include_router(attendance_router)
app.include_router(liveness_router)
@app.get("/")
def home():
    return {"message": "FaceNet API Running"}