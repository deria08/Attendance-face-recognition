from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import logging
from services.liveness_service import liveness_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/liveness", tags=["liveness"])

MAX_FRAMES = 45
# Mapping challenge ke instruksi user-friendly
CHALLENGE_DISPLAY = {
    "blink": "Silakan kedipkan kedua mata",
    "nod": "Silakan anggukkan kepala",
    "shake": "Silakan gelengkan kepala",
    "turn_left": "Silakan hadapkan wajah ke kiri",
    "turn_right": "Silakan hadapkan wajah ke kanan",
}


@router.post("/challenge")
async def create_challenge(user_id: str = Form(...)):
    """Buat session liveness dengan 2 challenge acak."""
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id required"
        )
    result = liveness_service.create_session(user_id)
    challenge = result.get("next_challenge")

    if challenge:
        result["instruction"] = CHALLENGE_DISPLAY.get(
            challenge["type"],
            ""
        )
    # result['instruction'] = CHALLENGE_DISPLAY.get(result.get('next_challenge', ''), '')
    return result


@router.post("/verify")
async def verify_challenge(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Verifikasi challenge dari 12-15 frame."""
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="session_id required"
        )
    
    if len(files) < 10:
        raise HTTPException(
            status_code=400,
            detail="Minimal 10 frame diperlukan"
        )
    # Batasi frame
    if len(files) > MAX_FRAMES:
        files = files[:MAX_FRAMES]
    
    # Baca semua frame
    frame_bytes = []
    for f in files:
        try:
            fb = await f.read()
            frame_bytes.append(fb)
        except Exception as e:
            logger.exception("Failed reading uploaded frame: %s", e)    
            continue
    
    if len(frame_bytes) < 3:
        raise HTTPException(status_code=400, detail="Frame tidak cukup")
    
    result = liveness_service.verify_challenge(session_id, frame_bytes)
    if result.get("session_invalid"):
        logger.warning(
            "Invalid liveness session: %s",
            session_id
        )
    
    # Tambahkan instruksi jika ada next_challenge
    # if 'next_challenge' in result and result['next_challenge']:
    #     result['instruction'] = CHALLENGE_DISPLAY.get(result['next_challenge'], '')
    if "next_challenge" in result and result["next_challenge"]:

        challenge = result["next_challenge"]

        result["instruction"] = CHALLENGE_DISPLAY.get(
            challenge["type"],
            ""
        )
    return result


@router.post("/reset")
async def reset_challenge(session_id: str = Form(...)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    return liveness_service.reset_session(session_id)


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    return liveness_service.get_status(session_id)