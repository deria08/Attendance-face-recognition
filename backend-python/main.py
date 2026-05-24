from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import test_connection
from routes.attendance import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_connection()
app.include_router(router, prefix="/api", tags=["attendance"])

@app.get("/")
def home():
    return {"message": "FaceNet API Running"}
# import cv2
# from fastapi import FastAPI, UploadFile, File, Form
# from keras_facenet import FaceNet
# import numpy as np
# from numpy.linalg import norm
# from datetime import datetime
# from fastapi.middleware.cors import CORSMiddleware
# from pymongo import MongoClient
# import math
# from typing import List, Optional
# from datetime import datetime, timedelta
# # import mediapipe as mp  # ← perbaikan di sini

# # =========================
# # MediaPipe Face Mesh
# # =========================
# # face_mesh = mp.solutions.face_mesh.FaceMesh(
# #     static_image_mode=False,
# #     max_num_faces=1,
# #     refine_landmarks=True,
# #     min_detection_confidence=0.5,
# #     min_tracking_confidence=0.5
# # )

# # def eye_aspect_ratio(landmarks, eye_indices):
# #     p1 = landmarks[eye_indices[0]]
# #     p2 = landmarks[eye_indices[1]]
# #     p3 = landmarks[eye_indices[2]]
# #     p4 = landmarks[eye_indices[3]]
# #     p5 = landmarks[eye_indices[4]]
# #     p6 = landmarks[eye_indices[5]]
# #     vertical1 = math.hypot(p2.x - p4.x, p2.y - p4.y)
# #     vertical2 = math.hypot(p3.x - p5.x, p3.y - p5.y)
# #     horizontal = math.hypot(p1.x - p6.x, p1.y - p6.y)
# #     ear = (vertical1 + vertical2) / (2.0 * horizontal)
# #     return ear

# def detect_blink_multiframe(images_bytes_list, ear_thresh=0.2):
#     # ears = []
#     # valid_frame_count = 0
#     # for img_bytes in images_bytes_list:
#     #     nparr = np.frombuffer(img_bytes, np.uint8)
#     #     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     #     if img is None:
#     #         continue
#     #     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     #     results = face_mesh.process(img_rgb)
#     #     if not results.multi_face_landmarks:
#     #         continue
#     #     face_landmarks = results.multi_face_landmarks[0]
#     #     left_eye_indices = [33, 160, 158, 133, 153, 144]
#     #     right_eye_indices = [362, 385, 387, 263, 373, 380]
#     #     landmarks = face_landmarks.landmark
#     #     ear_left = eye_aspect_ratio(landmarks, left_eye_indices)
#     #     ear_right = eye_aspect_ratio(landmarks, right_eye_indices)
#     #     ear = (ear_left + ear_right) / 2.0
#     #     ears.append(ear)
#     #     valid_frame_count += 1
#     # if valid_frame_count < 2:
#         return True
#     # has_open = any(e > ear_thresh for e in ears)
#     # has_closed = any(e < ear_thresh for e in ears)
#     # return has_open and has_closed
# # =========================
# # KONEKSI MONGODB
# # =========================
# client = MongoClient('mongodb+srv://deri123:OIGj9gU2HvSAhRr1@cluster0.nroolbp.mongodb.net/faceDB?retryWrites=true&w=majority')
# db = client['faceDB']
# faces_collection = db['faces']         # untuk menyimpan embedding wajah
# attendance_collection = db['attendances']  # untuk log absensi

# # Test koneksi
# try:
#     client.admin.command('ping')
#     print("✅ MongoDB connected successfully")
# except Exception as e:
#     print("❌ MongoDB connection error:", e)

# # =========================
# # APP FASTAPI
# # =========================
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # =========================
# # MODEL
# # =========================
# embedder = FaceNet()

# # =========================
# # HELPER FUNCTIONS
# # =========================
# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     return np.dot(a, b) / (norm(a) * norm(b))

# # =========================
# # ROUTES
# # =========================
# @app.get("/")
# def home():
#     return {"message": "FaceNet API Running"}

# @app.post("/extract-embedding")
# async def extract_embedding(file: UploadFile = File(...)):
#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     faces = embedder.extract(img, threshold=0.95)
#     if len(faces) == 0:
#         return {"error": "Wajah tidak ditemukan"}
#     return {"embedding": faces[0]["embedding"].tolist()}

# # =========================
# # REGISTER FACE
# # =========================
# @app.post("/register-face")
# async def register_face(name: str, file: UploadFile = File(...)):
#     print(f"🔥 Registrasi untuk: {name}")
#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     # Setelah cv2.imdecode
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)   # konversi ke RGB

#     # Gunakan img_rgb untuk ekstraksi
#     faces = embedder.extract(img_rgb, threshold=0.60)  # lebih longgar
#     print(f"Jumlah wajah terdeteksi: {len(faces)}")

#     if len(faces) == 0:
#         return {"error": "Wajah tidak ditemukan"}
#     if len(faces) > 1:
#         return {"error": "Terdapat lebih dari satu wajah"}

#     box = faces[0]["box"]
#     x, y, w, h = box
#     print(f"Ukuran wajah: {w}x{h}")

#     if w < 50 or h < 50:
#         return {"error": "Wajah terlalu kecil / jauh"}

#     embedding = faces[0]["embedding"]
#     with open(f"debug_{name}.jpg", "wb") as f:
#         f.write(contents)
#     print(f"Gambar disimpan ke debug_{name}.jpg, ukuran: {len(contents)} bytes")
#     print("✅ Embedding berhasil diekstrak")

#     # Simpan ke collection faces
#     result = faces_collection.update_one(
#         {"name": name},
#         {"$set": {"embedding": embedding.tolist(), "registered_at": datetime.now()}},
#         upsert=True
#     )
#     print(f"✅ Update MongoDB: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
    
#     return {"message": "Registrasi wajah berhasil", "name": name}
    

# # =========================
# # VERIFY FACE (optional, tidak dipakai frontend tapi bisa dipertahankan)
# # =========================
# @app.post("/verify-face")
# async def verify_face(name: str, file: UploadFile = File(...)):
#     face = faces_collection.find_one({"name": name})
#     if not face:
#         return {"error": "User belum registrasi wajah"}

#     saved_embedding = np.array(face["embedding"])

#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#     faces = embedder.extract(img, threshold=0.95)
#     if len(faces) == 0:
#         return {"error": "Wajah tidak ditemukan"}
#     if len(faces) > 1:
#         return {"error": "Terdapat lebih dari satu wajah"}

#     box = faces[0]["box"]
#     x, y, w, h = box
#     if w < 50 or h < 50:
#         return {"error": "Wajah terlalu kecil / jauh"}

#     new_embedding = faces[0]["embedding"]
#     similarity = cosine_similarity(new_embedding, saved_embedding)
#     is_match = bool(similarity > 0.75)

#     return {
#         "name": name,
#         "similarity": float(similarity),
#         "match": is_match
#     }

# # =========================
# # ATTENDANCE
# # =========================
# from fastapi import FastAPI, UploadFile, File, Form  # tambahkan Form

# # ... (kode lain tetap sama) ...

# @app.post("/attendance")
# async def attendance(
#     name: str = Form(...),
#     lat: Optional[float] = Form(None),
#     lon: Optional[float] = Form(None),
#     files: List[UploadFile] = File(...)
# ):
#     # ===== LOKASI VALIDASI =====
#     ALLOWED_LAT = -6.711007754906387
#     ALLOWED_LON = 111.05734318875855
#     MAX_RADIUS_KM = 0.5

#     if lat is None or lon is None:
#         return {"error": "Lokasi tidak dikirim. Pastikan GPS aktif."}
    
#     R = 6371
#     dlat = math.radians(lat - ALLOWED_LAT)
#     dlon = math.radians(lon - ALLOWED_LON)
#     a = math.sin(dlat/2)**2 + math.cos(math.radians(ALLOWED_LAT)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
#     c = 2 * math.asin(math.sqrt(a))
#     distance = R * c
#     if distance > MAX_RADIUS_KM:
#         return {"error": f"Anda berada di luar radius absensi ({distance:.2f} km dari kampus)"}
#     print(f"Lokasi valid, jarak: {distance:.2f} km")

#     # ===== BACA SEMUA FILE =====
#     if len(files) < 3:
#         return {"error": "Kirim minimal 3 frame untuk liveness detection"}
    
#     image_bytes_list = []
#     for file in files:
#         contents = await file.read()
#         image_bytes_list.append(contents)
    
#     # ===== LIVENESS DETECTION (BLINK) =====
#     is_live = detect_blink_multiframe(image_bytes_list, ear_thresh=0.2)
#     if not is_live:
#         return {"error": "Liveness detection gagal. Pastikan Anda mengedipkan mata saat pengambilan frame."}
#     print("Liveness detection berhasil (kedipan terdeteksi)")

#     # ===== VERIFIKASI WAJAH (gunakan frame pertama) =====
#     main_img_bytes = image_bytes_list[0]
#     nparr = np.frombuffer(main_img_bytes, np.uint8)
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
#     faces = embedder.extract(img_rgb, threshold=0.60)
#     if len(faces) == 0:
#         return {"error": "Wajah tidak terdeteksi pada frame utama"}
#     if len(faces) > 1:
#         return {"error": "Terdeteksi lebih dari satu wajah"}
    
#     # Ambil embedding dari frame pertama
#     new_embedding = faces[0]["embedding"]
#     box = faces[0]["box"]
#     x, y, w, h = box
#     if w < 30 or h < 30:
#         return {"error": "Wajah terlalu kecil / jauh"}
    
#     # Cari data wajah terdaftar
#     face = faces_collection.find_one({"name": name})
#     if not face:
#         return {"error": "User belum registrasi wajah"}
#     saved_embedding = np.array(face["embedding"])
    
#     similarity = cosine_similarity(new_embedding, saved_embedding)
#     is_match = bool(similarity > 0.75)
#     print(f"Similarity: {similarity}, is_match: {is_match}")
    
#     now = datetime.now()
    
#     if not is_match:
#         attendance_collection.insert_one({
#             "name": name,
#             "timestamp": now,
#             "status": "failed",
#             "similarity": float(similarity),
#             "message": "Wajah tidak cocok"
#         })
#         return {
#             "status": "failed",
#             "message": "Wajah tidak cocok",
#             "similarity": float(similarity)
#         }
    
#         # ===== CEK APAKAH SUDAH ABSEN HARI INI =====
#     start_day = datetime(now.year, now.month, now.day)
#     end_day = start_day + timedelta(days=1)

#     existing_attendance = attendance_collection.find_one({
#         "name": name,
#         "status": "success",
#         "timestamp": {
#             "$gte": start_day,
#             "$lt": end_day
#         }
#     })

#     if existing_attendance:
#         return {
#             "status": "failed",
#             "message": "Anda sudah melakukan absensi hari ini"
#         }
    
#     # Sukses
#     attendance_collection.insert_one({
#         "name": name,
#         "timestamp": now,
#         "status": "success",
#         "similarity": float(similarity),
#         "message": "Absensi berhasil"
#     })
#     return {
#         "status": "success",
#         "message": "Absensi berhasil",
#         "data": {
#             "name": name,
#             "time": now.strftime("%Y-%m-%d %H:%M:%S"),
#             "similarity": float(similarity)
#         }
#     }

# # =========================
# # GET ATTENDANCE HISTORY
# # =========================
# @app.get("/attendance-history")
# def attendance_history():
#     logs = list(attendance_collection.find({}, {"_id": 0}).sort("timestamp", -1))
#     return logs