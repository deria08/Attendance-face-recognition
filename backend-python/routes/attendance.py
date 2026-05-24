from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
import numpy as np
from services.face_service import register_face, verify_face, extract_face_embedding
from services.attendance_service import has_attended_today, save_attendance_log, has_attended_today_course
from services.location_service import validate_location
from services.liveness_service import detect_blink_multiframe
from services.meeting_service import get_active_meeting
from config.database import faces_collection, attendance_collection, db, courses_collection, enrollments_collection,users_collection
from utils.similarity import cosine_similarity
from datetime import datetime, timedelta
from pydantic import BaseModel
from bson import ObjectId
import asyncio
import math

class ManualUpdateRequest(BaseModel):
    name: str
    course_kode: str
    pertemuan: int
    status: str

router = APIRouter()

# Helper untuk sync operation
async def find_one_sync(collection, filter):
    return await asyncio.to_thread(collection.find_one, filter)

# Helper untuk mapping hari (Indonesia ke angka)
hari_map = {
    "Senin": 0, "Selasa": 1, "Rabu": 2, "Kamis": 3, "Jumat": 4, "Sabtu": 5, "Minggu": 6
}
# mapping kebalikan
hari_indonesia = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

@router.post("/register-face")
async def register_face_endpoint(name: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    result, error = register_face(name, contents)
    if error:
        return {"error": error}
    return {"message": "Registrasi wajah berhasil", "name": name}

@router.post("/verify-face")
async def verify_face_endpoint(name: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    result, error = verify_face(name, contents)
    if error:
        return {"error": error}
    return result

@router.post("/attendance")
async def attendance_endpoint(
    name: str = Form(...),
    course_kode: str = Form(...),
    pertemuan_aktif: Optional[int] = Form(None),  # tidak digunakan, hanya untuk kompatibilitas
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    files: List[UploadFile] = File(...)
):
    # 1. Validasi lokasi
    ok, msg = validate_location(lat, lon)
    if not ok:
        return {"error": msg}
    print(msg)

    # 2. Validasi liveness
    if len(files) < 3:
        return {"error": "Kirim minimal 3 frame untuk liveness detection"}
    image_bytes_list = [await f.read() for f in files]
    is_live = detect_blink_multiframe(image_bytes_list, ear_thresh=0.2)
    if not is_live:
        return {"error": "Liveness detection gagal. Pastikan Anda mengedipkan mata saat pengambilan frame."}
    print("Liveness detection berhasil")

    # 3. Verifikasi wajah (frame pertama) - perlu nama user dan embedding
    main_img_bytes = image_bytes_list[0]
    embedding, error = extract_face_embedding(main_img_bytes)
    if error:
        return {"error": error}
    print(f"Step 3 - face extraction done, error: {error}")
    if error:
        print(f"Returning error: {error}")
        return {"error": error}

    face = faces_collection.find_one({"name": name})
    print(f"Step 3b - face found: {face is not None}")
    if not face:
        return {"error": "User belum registrasi wajah"}
    saved_embedding = np.array(face["embedding"])
    similarity = cosine_similarity(np.array(embedding), saved_embedding)
    is_match = similarity > 0.75
    print(f"Step 3c - similarity: {similarity}, is_match: {is_match}")
    if not is_match:
        return {"status": "failed", "message": "Wajah tidak cocok", "similarity": similarity}

    # 4. Dapatkan data mahasiswa dan course
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    print(f"Step 4 - user found: {user is not None}")
    if not user:
        return {"error": "Mahasiswa tidak ditemukan"}
    user_id = user["_id"]
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    print(f"Step 5 - course found: {course is not None}")
    if not course:
        return {"error": "Mata kuliah tidak ditemukan"}
    course_id = course["_id"]

    # 5. Cek enrollment
    enrollment = await asyncio.to_thread(enrollments_collection.find_one, {
        "mahasiswa": user_id,
        "course": course_id
    })
    print(f"Step 6 - enrollment found: {enrollment is not None}")
    if not enrollment:
        return {"error": "Anda tidak terdaftar di mata kuliah ini"}

    # 6. Cek meeting aktif
    active_meeting = await get_active_meeting(course_id)
    print(f"Step 7 - active meeting: {active_meeting is not None}")
    if not active_meeting:
        return {"error": "Tidak ada sesi absensi aktif untuk mata kuliah ini"}
    pertemuan_aktif = active_meeting["pertemuan_ke"]
    meeting_id = active_meeting["_id"]

    # 7. Hitung keterlambatan berdasarkan waktu buka meeting
    start_time = active_meeting["start_time"]
    toleransi = course.get('late_tolerance_minutes', 15)
    waktu_sekarang = datetime.now()
    batas_terlambat = start_time + timedelta(minutes=toleransi)

    if waktu_sekarang > batas_terlambat:
        status_absensi = "late"
        pesan = f"Terlambat (melebihi batas {toleransi} menit dari buka sesi)"
    else:
        status_absensi = "success"
        pesan = "Absensi berhasil"

    # 8. Cek apakah sudah absen hari ini uns  tuk course dan pertemuan ini
    if has_attended_today(user_id, course_id, pertemuan_aktif):
        return {"status": "failed", "message": f"Anda sudah absen untuk {course['nama_mk']} pertemuan {pertemuan_aktif} hari ini"}

    print(f"=== MENYIMPAN LOG ===")
    print(f"user_id: {user_id}, course_id: {course_id}, meeting_id: {meeting_id}, pertemuan: {pertemuan_aktif}, status: {status_absensi}, similarity: {similarity}")
    # 9. Simpan log
    try:
        await save_attendance_log(user_id, course_id, meeting_id, pertemuan_aktif, status_absensi, similarity, pesan, lat=lat, lon=lon)
    except Exception as e:
        return {"error": f"Gagal menyimpan ke database: {str(e)}"}
    # print(f"Inserting doc: {doc}")
    # result = attendance_collection.insert_one(doc)
    # print(f"Inserted id: {result.inserted_id}")
    return {
        "status": status_absensi,
        "message": pesan,
        "data": {
            "name": name,
            "course": course['nama_mk'],
            "time": waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S"),
            "similarity": similarity
        }
    }

@router.get("/attendance-history")
async def attendance_history():
    logs = list(attendance_collection.find({}, {"_id": 0}).sort("timestamp", -1))
    return logs

@router.get("/attendance-status")
async def check_attendance_today(name: str, course_kode: str):
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    if not user:
        return {"hasAttended": False}
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    if not course:
        return {"hasAttended": False}
    has_attended = has_attended_today_course(user["_id"], course["_id"])
    return {"hasAttended": has_attended}

@router.get("/attendance-recap")
def attendance_recap():
    # Di sini nanti perlu disesuaikan untuk menampilkan rekap per course
    # Untuk sementara tetap seperti semula
    face_logs = list(attendance_collection.find({"status": {"$in": ["success", "late"]}}, {"_id": 0}))
    manual_collection = db['manual_attendance']
    manual_logs = list(manual_collection.find({}, {"_id": 0}))
    status_manual = log.get('status')
    if status_manual == 'manual':
        symbol = '✔'  # atau simbol khusus 'M'
        
    combined = {}
    for log in face_logs:
        name = log.get('name')
        pertemuan = log.get('pertemuan')
        if name not in combined:
            combined[name] = {"nama": name, "attendance": [""] * 16}
        # Tampilkan '✔' untuk success, 'L' untuk late
        symbol = '✔' if log['status'] == 'success' else ('L' if log['status'] == 'late' else '')
        combined[name]["attendance"][pertemuan - 1] = symbol

    for manual in manual_logs:
        name = manual.get('name')
        pertemuan = manual.get('pertemuan')
        status = manual.get('status')
        if name not in combined:
            combined[name] = {"nama": name, "attendance": [""] * 16}
        combined[name]["attendance"][pertemuan - 1] = status

    return list(combined.values())


@router.get("/attendance/manual-status")
def get_manual_status():
    manual_collection = db['manual_attendance']
    logs = list(manual_collection.find({}, {"_id": 0}))
    return logs

@router.put("/attendance/manual-update")
def manual_update_attendance(req: ManualUpdateRequest):
    # Cari user_id dan course_id
    user = users_collection.find_one({"name": req.name, "role": "mahasiswa"})
    if not user:
        return {"error": "Mahasiswa tidak ditemukan"}
    course = courses_collection.find_one({"kode_mk": req.course_kode})
    if not course:
        return {"error": "Course tidak ditemukan"}
    user_id = user["_id"]
    course_id = course["_id"]
    
    manual_collection = db['manual_attendance']
    manual_collection.update_one(
        {"user_id": user_id, "course_id": course_id, "pertemuan": req.pertemuan},
        {"$set": {"status": req.status, "updated_at": datetime.now()}},
        upsert=True
    )
    return {"message": "Status updated"}

@router.get("/courses/mahasiswa")
async def get_mahasiswa_courses(user_id: str = None, name: str = None):
    if user_id:
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id), "role": "mahasiswa"})
    else:
        user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    if not user:
        return []
    enrolls = await asyncio.to_thread(list, enrollments_collection.find({"mahasiswa": user['_id']}))
    courses = []
    for e in enrolls:
        course = await asyncio.to_thread(courses_collection.find_one, {"_id": e['course']})
        if course:
            courses.append({"kode_mk": course['kode_mk'], "nama_mk": course['nama_mk'], "id": str(course['_id'])})
    return courses
@router.get("/attendance-recap-by-course")
async def attendance_recap_by_course(course_kode: str):
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    if not course:
        return []
    course_id = course["_id"]
    
    # Ambil semua enrollment
    enrolls = await asyncio.to_thread(list, enrollments_collection.find({"course": course_id}))
    user_ids = [e["mahasiswa"] for e in enrolls]
    
    # Ambil nama mahasiswa untuk display
    users = await asyncio.to_thread(list, users_collection.find({"_id": {"$in": user_ids}}))
    user_map = {u["_id"]: u["name"] for u in users}
    status_manual = log.get('status')
    if status_manual == 'manual':
        symbol = '✔'  # atau simbol khusus 'M'
    # Ambil logs absensi
    face_logs = await asyncio.to_thread(list, attendance_collection.find({
        "course_id": course_id,
        "user_id": {"$in": user_ids},
        "status": {"$in": ["success", "late"]}
    }))
    
    manual_logs = await asyncio.to_thread(list, db['manual_attendance'].find({
        "course_id": course_id,
        "user_id": {"$in": user_ids}
    }))
    
    # Inisialisasi combined dengan semua mahasiswa
    combined = {}
    for name in user_map.values():
        combined[name] = {"nama": name, "attendance": [""] * 16}
    
    # Proses face logs
    for log in face_logs:
        user_id = log.get('user_id')
        name = user_map.get(user_id)
        if not name:
            continue
        pertemuan = log.get('pertemuan')
        if 1 <= pertemuan <= 16:
            symbol = '✔' if log['status'] == 'success' else 'L'
            combined[name]["attendance"][pertemuan - 1] = symbol
    
    # Proses manual logs (override)
    for manual in manual_logs:
        user_id = manual.get('user_id')
        name = user_map.get(user_id)
        if not name:
            continue
        pertemuan = manual.get('pertemuan')
        status = manual.get('status')
        if 1 <= pertemuan <= 16 and status:
            combined[name]["attendance"][pertemuan - 1] = status
    
    return list(combined.values())

@router.post("/attendance-manual")
async def manual_attendance(
    name: str = Form(...),
    course_kode: str = Form(...)
):
    # 1. Validasi mahasiswa
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    if not user:
        return {"error": "Mahasiswa tidak ditemukan"}
    user_id = user["_id"]
    
    # 2. Validasi course
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    if not course:
        return {"error": "Mata kuliah tidak ditemukan"}
    course_id = course["_id"]
    
    # 3. Cek enrollment
    enrollment = await asyncio.to_thread(enrollments_collection.find_one, {
        "mahasiswa": user_id,
        "course": course_id
    })
    if not enrollment:
        return {"error": "Anda tidak terdaftar di mata kuliah ini"}
    
    # 4. Cek meeting aktif (wajib ada sesi)
    active_meeting = await get_active_meeting(course_id)
    if not active_meeting:
        return {"error": "Tidak ada sesi absensi aktif untuk mata kuliah ini"}
    pertemuan_aktif = active_meeting["pertemuan_ke"]
    meeting_id = active_meeting["_id"]
    
    # 5. Cek sudah absen hari ini
    if has_attended_today(user_id, course_id, pertemuan_aktif):
        return {"status": "failed", "message": "Anda sudah absen untuk pertemuan ini"}
    
    # 6. Simpan log dengan status 'manual'
    save_attendance_log(user_id, course_id, meeting_id, pertemuan_aktif, "manual", 0.0, "Absensi manual oleh mahasiswa")
    
    return {
        "status": "success",
        "message": "Absensi manual berhasil",
        "data": {
            "name": name,
            "course": course['nama_mk'],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }