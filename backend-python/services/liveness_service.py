# import cv2
# import numpy as np
# import math

# # ================================================
# # LIVENESS DETECTION (BLINK DETECTION)
# # ================================================

# # Coba import mediapipe, jika gagal maka set flag
# try:
#     import mediapipe as mp
#     face_mesh = mp.solutions.face_mesh.FaceMesh(
#         static_image_mode=False,
#         max_num_faces=1,
#         refine_landmarks=True,
#         min_detection_confidence=0.5,
#         min_tracking_confidence=0.5
#     )
#     MEDIAPIPE_AVAILABLE = True
#     print("✅ MediaPipe loaded for liveness detection")
# except Exception as e:
#     MEDIAPIPE_AVAILABLE = False
#     print("⚠️ MediaPipe not available, liveness detection disabled:", e)

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

# def detect_blink_multiframe(images_bytes_list, ear_thresh=0.2):
#     if not MEDIAPIPE_AVAILABLE:
#         print("⚠️ Liveness detection skipped (MediaPipe not available)")
#         return True   # Bypass liveness detection jika mediapipe error

#     ears = []
#     valid_frame_count = 0
#     for img_bytes in images_bytes_list:
#         nparr = np.frombuffer(img_bytes, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#         if img is None:
#             continue
#         img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(img_rgb)
#         if not results.multi_face_landmarks:
#             continue
#         face_landmarks = results.multi_face_landmarks[0]
#         left_eye_indices = [33, 160, 158, 133, 153, 144]
#         right_eye_indices = [362, 385, 387, 263, 373, 380]
#         landmarks = face_landmarks.landmark
#         ear_left = eye_aspect_ratio(landmarks, left_eye_indices)
#         ear_right = eye_aspect_ratio(landmarks, right_eye_indices)
#         ear = (ear_left + ear_right) / 2.0
#         ears.append(ear)
#         valid_frame_count += 1

#     if valid_frame_count < 2:
#         return False
#     has_open = any(e > ear_thresh for e in ears)
#     has_closed = any(e < ear_thresh for e in ears)
#     return has_open and has_closed
import cv2
import numpy as np
import math

# ================================================
# DETEKSI KEDIPAN MATA MENGGUNAKAN HAAR CASCADE
# ================================================

# Inisialisasi cascade classifier untuk mata
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
if eye_cascade.empty():
    print("⚠️ Haar cascade for eye not found, liveness detection disabled")
    MEDIAPIPE_AVAILABLE = False
else:
    MEDIAPIPE_AVAILABLE = True
    print("✅ Liveness detection using Haar cascade is ready")

def detect_blink_multiframe(images_bytes_list, ear_thresh=0.2):
    """Deteksi kedipan dengan membandingkan jumlah frame yang memiliki mata terbuka vs tertutup"""
    if not MEDIAPIPE_AVAILABLE:
        return True  # bypass jika cascade tidak tersedia

    eye_open_frames = 0
    eye_closed_frames = 0

    for img_bytes in images_bytes_list:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Deteksi mata (sederhana: jika ada minimal 1 mata, anggap terbuka)
        if len(eyes) >= 1:
            eye_open_frames += 1
        else:
            eye_closed_frames += 1

    # Kebutuhan minimal 2 frame valid
    total_frames = eye_open_frames + eye_closed_frames
    if total_frames < 2:
        return False

    # Anggap ada kedipan jika setidaknya satu frame mata terbuka dan satu frame mata tertutup
    return eye_open_frames > 0 and eye_closed_frames > 0