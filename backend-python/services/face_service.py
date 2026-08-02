import cv2 
import numpy as np 
import mediapipe as mp 
from typing import List, Optional
from keras_facenet import FaceNet
from datetime import datetime
from config.database import faces_collection
from utils.similarity import cosine_similarity

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

embedder = FaceNet()

def extract_face_landmarks_from_bytes(image_bytes: bytes) -> Optional[List]:
    """
    Ekstrak landmark MediaPipe Face Mesh dari bytes gambar.
    Mengembalikan list landmark (normalized) jika berhasil, atau None.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            return None
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)
        if (
            not result.multi_face_landmarks
            or len(result.multi_face_landmarks) != 1
        ):
            return None
        return result.multi_face_landmarks[0].landmark
    except Exception as e:
        print(f"[FaceMesh] {e}")
        return None
    
def extract_landmarks_sequence(images_bytes_list):
    """
    Mengubah list image bytes menjadi list landmark.
    Frame yang gagal otomatis dilewati.
    """
    sequence = []

    for image in images_bytes_list:
        landmark = extract_face_landmarks_from_bytes(image)

        if landmark is not None:
            sequence.append(landmark)

    return sequence


def extract_face_embedding(image_bytes, threshold=0.60):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, "Gambar tidak valid"
    # Brightness enhancement
    img = cv2.convertScaleAbs(img, alpha=1.5, beta=40)
    # cek brightness
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray)
    if brightness < 40:
        return None, "Pencahayaan terlalu gelap"
    # Denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = embedder.extract(img_rgb, threshold=threshold)
    if len(faces) == 0:
        return None, "Wajah tidak ditemukan"
    if len(faces) > 1:
        return None, "Terdapat lebih dari satu wajah"
    box = faces[0]["box"]
    w, h = box[2], box[3]
    if w < 50 or h < 50:
        return None, "Wajah terlalu kecil / jauh"
    embedding = faces[0]["embedding"]
    return embedding.tolist(), None

def register_face(name, image_bytes):
    embedding, error = extract_face_embedding(image_bytes, threshold=0.60)
    if error:
        return None, error
    result = faces_collection.update_one(
        {"name": name},
        {"$set": {"embedding": embedding, "registered_at": datetime.now()}},
        upsert=True
    )
    return result, None

def verify_face(name, image_bytes):
    face = faces_collection.find_one({"name": name})
    if not face:
        return None, "User belum registrasi wajah"
    saved_embedding = np.array(face["embedding"])
    embedding, error = extract_face_embedding(image_bytes)
    if error:
        return None, error
    similarity = cosine_similarity(np.array(embedding), saved_embedding)
    is_match = similarity > 0.65
    return {"similarity": float(similarity), "match": is_match}, None