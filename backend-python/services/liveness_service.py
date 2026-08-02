# import cv2
# import numpy as np
# import math
# import mediapipe as mp

# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     static_image_mode=False,
#     max_num_faces=1,
#     refine_landmarks=True,
#     min_detection_confidence=0.5,
#     min_tracking_confidence=0.5
# )

# def eye_aspect_ratio(landmarks, eye_indices):
#     p1 = landmarks[eye_indices[0]]
#     p2 = landmarks[eye_indices[1]]
#     p3 = landmarks[eye_indices[2]]
#     p4 = landmarks[eye_indices[3]]
#     p5 = landmarks[eye_indices[4]]
#     p6 = landmarks[eye_indices[5]]
#     vertical1 = math.hypot(p2.x - p4.x, p2.y - p4.y)
#     vertical2 = math.hypot(p3.x - p5.x, p3.y - p5.y)
#     horizontal = math.hypot(p1.x - p6.x, p1.y - p6.y)
#     ear = (vertical1 + vertical2) / (2.0 * horizontal)
#     return ear

# def compute_head_pose(landmarks):
#     nose = landmarks[1]
#     chin = landmarks[199]
#     left_eye_outer = landmarks[33]
#     right_eye_outer = landmarks[263]
#     nose_chin_vec = (nose.x - chin.x, nose.y - chin.y, nose.z - chin.z)
#     pitch = math.degrees(math.atan2(nose_chin_vec[1], math.sqrt(nose_chin_vec[0]**2 + nose_chin_vec[2]**2)))
#     eye_center_x = (left_eye_outer.x + right_eye_outer.x) / 2
#     yaw = math.degrees(math.atan2(nose.x - eye_center_x, nose.z))
#     return yaw, pitch

# def detect_head_movement(yaw_list, pitch_list, yaw_thresh=15, pitch_thresh=10):
#     if len(yaw_list) < 2:
#         return False
#     delta_yaw = max(yaw_list) - min(yaw_list)
#     delta_pitch = max(pitch_list) - min(pitch_list)
#     return delta_yaw > yaw_thresh or delta_pitch > pitch_thresh

# def detect_blink_multiframe(images_bytes_list, ear_thresh=0.2, require_head_movement=False):
#     ears = []
#     yaws = []
#     pitches = []

#     for idx, img_bytes in enumerate(images_bytes_list):
#         nparr = np.frombuffer(img_bytes, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#         if img is None:
#             continue
#         img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(img_rgb)
#         if not results.multi_face_landmarks:
#             continue
#         landmarks = results.multi_face_landmarks[0].landmark

#         left_eye_indices = [33, 159, 158, 133, 153, 145]   # ganti
#         right_eye_indices = [362, 386, 385, 263, 373, 374] # ganti
#         ear_left = eye_aspect_ratio(landmarks, left_eye_indices)
#         ear_right = eye_aspect_ratio(landmarks, right_eye_indices)
#         ear = (ear_left + ear_right) / 2.0
#         ears.append(ear)
#         print(f"DEBUG EAR frame {idx}: {ear:.4f}")   # tambah debug

#         yaw, pitch = compute_head_pose(landmarks)
#         yaws.append(yaw)
#         pitches.append(pitch)


#     print("EARS:", ears)
#     print("YAWS:", yaws)
#     print("PITCHES:", pitches)
#     print("Jumlah frame valid:", len(ears))
#     if len(ears) < 10:
#         print(f"❌ Liveness: hanya {len(ears)} frame valid (minimal 10)")
#         return False
    
#     baseline_ear = sum(ears[:2]) / 2
#     dynamic_thresh = max(0.2, baseline_ear * 0.9)
#     print(f"📊 Baseline EAR: {baseline_ear:.3f}, Threshold: {dynamic_thresh:.3f}")

#     state = "OPEN"
#     blink_detected = False
#     for ear in ears:
#         if state == "OPEN" and ear < dynamic_thresh:
#             state = "CLOSED"
#         elif state == "CLOSED" and ear > dynamic_thresh:
#             blink_detected = True
#             break
#     print(f"EAR={ear:.3f}, STATE={state}")
#     if not blink_detected:
#         print("❌ Liveness: tidak ada urutan kedipan natural")
#         return False

#     if require_head_movement:
#         head_moved = detect_head_movement(yaws, pitches)
#         if not head_moved:
#             print("❌ Liveness: gerakan kepala tidak terdeteksi")
#         return head_moved
#     else:
#         print("✅ Liveness berhasil (kedipan terdeteksi)")
#         return True
import secrets
import time
import logging
import random
from typing import Dict, List, Optional
from models.liveness_session import LivenessSession
from utils.landmark_utils import detect_motion
from services.face_service import extract_face_landmarks_from_bytes

logger = logging.getLogger(__name__)

# Session storage (gunakan Redis untuk production)
_sessions: Dict[str, LivenessSession] = {}
CLEANUP_INTERVAL = 60
_last_cleanup = time.time()


class LivenessService:
    CHALLENGES = [
    {
        "type": "blink",
        "count": 1
    },
    {
        "type": "nod",
        "count": 1
    },
    {
        "type": "nod",
        "count": 2
    },
    {
        "type": "shake",
        "count": 1
    },
    {
        "type": "shake",
        "count": 2
    },
    {
        "type": "turn_left",
        "count": 1
    },
    {
        "type": "turn_right",
        "count": 1
    }
]
    
    def __init__(self):
        self._cleanup()
    
    def create_session(self, user_id: str) -> Dict:
        """Buat session liveness baru dengan 2 challenge random."""
        self._cleanup()
        challenges = random.sample(self.CHALLENGES, 2)
        session_id = secrets.token_hex(16)
        session = LivenessSession(
            session_id=session_id,
            user_id=user_id,
            challenges=challenges
        )
        session.reset_challenge_timer()
        _sessions[session_id] = session
        # logger.info(f"Session created: {session_id} for user {user_id}, challenges: {challenges}")
        logger.info(
            "Session created: %s user=%s challenges=%s",
            session_id,
            user_id,
            challenges
        )
        data = session.to_dict()
        data["challenges"] = session.challenges
        return data
    
    def get_session(self, session_id: str) -> Optional[LivenessSession]:
        self._cleanup()
        session = _sessions.get(session_id)
        if session and session.is_expired():
            self._remove_session(session_id)
            return None
        return session
    
    def verify_challenge(self, session_id: str, frames: List[bytes]) -> Dict:
        """
        Verifikasi challenge dari sequence frame.
        Mengembalikan response dengan status, retry, atau completed.
        """
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Session tidak ditemukan atau expired', 'session_invalid': True}
        
        if session.failed:
            return {'error': 'Session sudah gagal', 'session_invalid': True}
        
        if session.completed:
            return {'error': 'Semua challenge sudah selesai', 'completed': True}
        
        # Cek timeout
        if session.is_challenge_timeout():
            logger.warning(f"Challenge timeout for session {session_id}")
            self._fail_session(session_id)
            return {'error': 'Waktu habis. Silakan mulai ulang.', 'session_invalid': True}
        
        # Ekstrak landmark dari setiap frame
        landmarks_seq = []

        valid_frames = 0
        invalid_frames = 0

        for fb in frames:

            lm = extract_face_landmarks_from_bytes(fb)

            if lm is None:
                invalid_frames += 1
                continue
            valid_frames += 1
            landmarks_seq.append(lm)
        total_frames = valid_frames + invalid_frames

        valid_ratio = valid_frames / max(total_frames, 1)

        logger.info(
            "Frame validation: valid=%d invalid=%d ratio=%.2f",
            valid_frames,
            invalid_frames,
            valid_ratio
        )
        if valid_ratio < 0.90:

            logger.warning(
                "Frame quality too low "
                "(valid=%s invalid=%s)",
                valid_frames,
                invalid_frames
            )

            session.increment_attempt()

            return {
                "error":
                    "Wajah harus terlihat jelas selama proses verifikasi.",
                "retry": True,
                "remaining_attempts":
                    session.remaining_attempts()
            }
        if len(landmarks_seq) < 10:
            logger.warning("Landmark sequence terlalu pendek")
            session.increment_attempt()
            return self._handle_attempt(session)
        
        
        # Verifikasi challenge
        current = session.get_next_challenge()
        if not current:
            return {'error': 'No challenge active', 'completed': True}
        if not current:
            return {
                "error": "Challenge tidak ditemukan"
            }
        challenge_type = current["type"]
        passed = detect_motion(
            landmarks_seq,
            current
        )
        
        if passed:
            logger.info(f"Challenge '{current}' passed for session {session_id}")
            has_next = session.advance()
            if not has_next:
                # Semua selesai
                self._remove_session(session_id)
                return {
                    'success': True,
                    'completed': True,
                    'message': 'Liveness detection berhasil!'
                }
            else:
                # Lanjut ke challenge berikutnya
                return {
                    'success': True,
                    'completed': False,
                    'current_step': session.current_step + 1,
                    'total_steps': len(session.challenges),
                    'next_challenge': session.get_next_challenge(),
                    'timeout_seconds': session.timeout_seconds,
                    'remaining_attempts': session.remaining_attempts(),
                    'message': f'Challenge berhasil! Lanjutkan ke challenge berikutnya.'
                }
        else:
            # Gagal
            session.increment_attempt()
            logger.warning(
                "Challenge failed: %s session=%s attempt=%d",
                current,
                session.session_id,
                session.attempt + 1
            )
            return self._handle_attempt(session)
    
    def _handle_attempt(self, session: LivenessSession) -> Dict:
        """Handle attempt dan return response retry atau gagal."""
        if session.attempt >= session.max_attempts:
            self._fail_session(session.session_id)
            return {
                'error': f'Gagal setelah {session.max_attempts} percobaan.',
                'session_invalid': True
            }
        else:
            return {
                'error': f"Challenge '{session.get_next_challenge()}' belum berhasil.",
                'retry': True,
                'remaining_attempts': session.remaining_attempts(),
            }
    
    def reset_session(self, session_id: str) -> Dict:

        if session_id in _sessions:
            self._remove_session(session_id)

        return {
            "message": "Session direset",
            "session_invalid": True
        }
    
    def get_status(self, session_id: str) -> Dict:
        session = self.get_session(session_id)

        if not session:
            return {
                "exists": False
            }

        return {
            "exists": True,
            "session": session.to_dict()
        }
        
    def _remove_session(self, session_id: str):
        if session_id in _sessions:
            del _sessions[session_id]
    
    def _fail_session(self, session_id: str):
        session = _sessions.get(session_id)
        if session:
            session.mark_failed()
            self._remove_session(session_id)
    
    def _cleanup(self):
        global _last_cleanup
        now = time.time()
        if now - _last_cleanup < CLEANUP_INTERVAL:
            return
        expired = [sid for sid, s in _sessions.items() if s.is_expired()]
        for sid in expired:
            del _sessions[sid]
        _last_cleanup = now
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")


# Singleton
liveness_service = LivenessService()