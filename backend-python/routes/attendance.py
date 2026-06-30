from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
import numpy as np
from services.pdf_export import generate_attendance_pdf
from services.face_service import register_face, verify_face, extract_face_embedding
from services.attendance_service import has_attended_today, save_attendance_log, has_attended_today_course
from services.location_service import validate_location
from services.liveness_service import detect_blink_multiframe
from services.meeting_service import get_active_meeting
from config.database import faces_collection, attendance_collection, db, courses_collection, enrollments_collection, users_collection
from utils.similarity import cosine_similarity
from datetime import datetime, timedelta, timezone
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
    # 1. Validasi user
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    if not user:
        raise HTTPException(status_code=400, detail="User tidak ditemukan")
    
    # 2. Ekstrak embedding
    contents = await file.read()
    embedding, error = extract_face_embedding(contents, threshold=0.60)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # 3. Simpan ke MongoDB (faces collection)
    try:
        faces_collection.update_one(
            {"name": name},
            {"$set": {
                "embedding": embedding,
                "user_id": user["_id"],        # ← tambah field user_id
                "registered_at": datetime.now()
            }},
            upsert=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {"message": "Registrasi wajah berhasil", "name": name}

@router.post("/verify-face")
async def verify_face_endpoint(name: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    result, error = verify_face(name, contents)
    if error:
        raise HTTPException(status_code=400, detail=error)
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
        raise HTTPException(status_code=400, detail=msg)
    print(msg)
    print("1. Validasi lokasi")

    # 2. Validasi liveness
    print("Jumlah file diterima:", len(files))
    if len(files) < 5:
        raise HTTPException(status_code=400, detail="Kirim minimal 5 frame untuk liveness detection")
    image_bytes_list = [await f.read() for f in files]
    print("Image bytes count:", len(image_bytes_list))
    is_live = detect_blink_multiframe(image_bytes_list, ear_thresh=0.2, require_head_movement=False)
    if not is_live:
        raise HTTPException(status_code=400, detail="Liveness detection gagal. Pastikan Anda mengedipkan mata.")
    print("Liveness detection berhasil")
    print("2. Validasi liveness")

    # 3. Verifikasi wajah (frame pertama)
    main_img_bytes = image_bytes_list[0]
    embedding, error = extract_face_embedding(main_img_bytes)
    if error:
        raise HTTPException(status_code=400, detail=error)
    print(f"Step 3 - face extraction done, error: {error}")

    face = faces_collection.find_one({"name": name})
    print(f"Step 3b - face found: {face is not None}")
    if not face:
        raise HTTPException(status_code=400, detail="User belum registrasi wajah")
    saved_embedding = np.array(face["embedding"])
    similarity = cosine_similarity(np.array(embedding), saved_embedding)
    is_match = similarity > 0.75
    print(f"Step 3c - similarity: {similarity}, is_match: {is_match}")
    if not is_match:
        raise HTTPException(status_code=400, detail="Wajah tidak cocok")
    print("3. Verifikasi wajah")

    # 4. Dapatkan data mahasiswa dan course
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    print(f"Step 4 - user found: {user is not None}")
    if not user:
        raise HTTPException(status_code=400, detail="Mahasiswa tidak ditemukan")
    user_id = user["_id"]
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    print(f"Step 5 - course found: {course is not None}")
    if not course:
        raise HTTPException(status_code=400, detail="Mata kuliah tidak ditemukan")
    course_id = course["_id"]
    print("4. Dapatkan user & course")

    # 5. Cek enrollment
    enrollment = await asyncio.to_thread(enrollments_collection.find_one, {
        "mahasiswa": user_id,
        "course": course_id
    })
    print(f"Step 6 - enrollment found: {enrollment is not None}")
    if not enrollment:
        raise HTTPException(status_code=400, detail="Anda tidak terdaftar di mata kuliah ini")
    print("5. Cek enrollment")

    # 6. Cek meeting aktif
    active_meeting = await get_active_meeting(course_id)
    print(f"Step 7 - active meeting: {active_meeting is not None}")
    if not active_meeting:
        raise HTTPException(status_code=400, detail="Tidak ada sesi absensi aktif")
    pertemuan_aktif = active_meeting["pertemuan_ke"]
    meeting_id = active_meeting["_id"]
    print("6. Cek meeting aktif")

    # 7. Hitung keterlambatan berdasarkan waktu buka meeting
    start_time = active_meeting["start_time"]
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    toleransi = course.get('late_tolerance_minutes', 15)
    waktu_sekarang = datetime.now(timezone.utc)
    batas_terlambat = start_time + timedelta(minutes=toleransi)

    if waktu_sekarang > batas_terlambat:
        status_absensi = "late"
        # Hitung selisih menit keterlambatan
        terlambat_menit = int((waktu_sekarang - start_time).total_seconds() / 60)
        pesan = f"Berhasil, namun Anda terlambat {terlambat_menit} menit dari waktu buka sesi (batas toleransi {toleransi} menit)."
    else:
        status_absensi = "success"
        pesan = "Absensi berhasil tepat waktu"

    # 8. Cek apakah sudah absen hari ini
    if has_attended_today(user_id, course_id, pertemuan_aktif):
        raise HTTPException(status_code=400, detail=f"Anda sudah absen untuk {course['nama_mk']} pertemuan {pertemuan_aktif} hari ini")
    else:
        print("✅ has_attended_today mengembalikan False -> lanjut simpan")
    print("8. Cek sudah absen hari ini")
    print(f"=== MENYIMPAN LOG ===")
    print(f"user_id: {user_id}, course_id: {course_id}, meeting_id: {meeting_id}, pertemuan: {pertemuan_aktif}, status: {status_absensi}, similarity: {similarity}")

    # 9. Simpan log
    try:
        await save_attendance_log(user_id, course_id, meeting_id, pertemuan_aktif, status_absensi, similarity, pesan, lat=lat, lon=lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan ke database: {str(e)}")

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
    # Gabungkan data dari face recognition dan manual attendance
    face_logs = list(attendance_collection.find({"status": {"$in": ["success", "late"]}}, {"_id": 0}))
    manual_collection = db['manual_attendance']
    manual_logs = list(manual_collection.find({}, {"_id": 0}))
    combined = {}
    for log in face_logs:
        name = log.get('name')
        pertemuan = log.get('pertemuan')
        if name not in combined:
            combined[name] = {"nama": name, "attendance": [""] * 16}
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
    user = users_collection.find_one({"name": req.name, "role": "mahasiswa"})
    if not user:
        raise HTTPException(status_code=400, detail="Mahasiswa tidak ditemukan")
    course = courses_collection.find_one({"kode_mk": req.course_kode})
    if not course:
        raise HTTPException(status_code=400, detail="Course tidak ditemukan")
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
    enrolls = await asyncio.to_thread(list, enrollments_collection.find({"course": course_id}))
    user_ids = [e["mahasiswa"] for e in enrolls]
    users = await asyncio.to_thread(list, users_collection.find({"_id": {"$in": user_ids}}))
    user_map = {u["_id"]: u["name"] for u in users}
    face_logs = await asyncio.to_thread(list, attendance_collection.find({
        "course_id": course_id,
        "user_id": {"$in": user_ids},
        "status": {"$in": ["success", "late"]}
    }))
    manual_logs = await asyncio.to_thread(list, db['manual_attendance'].find({
        "course_id": course_id,
        "user_id": {"$in": user_ids}
    }))
    combined = {}
    for name in user_map.values():
        combined[name] = {"nama": name, "attendance": [""] * 16}
    for log in face_logs:
        user_id = log.get('user_id')
        name = user_map.get(user_id)
        if not name:
            continue
        pertemuan = log.get('pertemuan')
        if 1 <= pertemuan <= 16:
            symbol = '✔' if log['status'] == 'success' else 'L'
            combined[name]["attendance"][pertemuan - 1] = symbol
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
    user = await asyncio.to_thread(users_collection.find_one, {"name": name, "role": "mahasiswa"})
    if not user:
        raise HTTPException(status_code=400, detail="Mahasiswa tidak ditemukan")
    user_id = user["_id"]
    course = await asyncio.to_thread(courses_collection.find_one, {"kode_mk": course_kode})
    if not course:
        raise HTTPException(status_code=400, detail="Mata kuliah tidak ditemukan")
    course_id = course["_id"]
    enrollment = await asyncio.to_thread(enrollments_collection.find_one, {
        "mahasiswa": user_id,
        "course": course_id
    })
    if not enrollment:
        raise HTTPException(status_code=400, detail="Anda tidak terdaftar di mata kuliah ini")
    active_meeting = await get_active_meeting(course_id)
    if not active_meeting:
        raise HTTPException(status_code=400, detail="Tidak ada sesi absensi aktif untuk mata kuliah ini")
    pertemuan_aktif = active_meeting["pertemuan_ke"]
    meeting_id = active_meeting["_id"]
    if has_attended_today(user_id, course_id, pertemuan_aktif):
        raise HTTPException(status_code=400, detail="Anda sudah absen untuk pertemuan ini")
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

@router.get("/attendance-stats")
async def attendance_stats(user_id: str):
    try:
        user_oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    total_present = attendance_collection.count_documents({
        "user_id": user_oid,
        "status": {"$in": ["success", "late"]}
    })
    total_late = attendance_collection.count_documents({
        "user_id": user_oid,
        "status": "late"
    })
    enrollments = enrollments_collection.count_documents({"mahasiswa": user_oid})
    total_meetings = enrollments * 16
    
    # ⭐ Ubah round menjadi 1 desimal
    attendance_rate = round((total_present / total_meetings * 100) if total_meetings > 0 else 0, 1)
    
    return {
        "total_present": total_present,
        "total_late": total_late,
        "attendance_rate": attendance_rate
    }
@router.delete("/reset-face")
async def reset_face(name: str):
    result = faces_collection.delete_one({"name": name})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Data wajah tidak ditemukan"
        )

    return {
        "message": "Embedding wajah berhasil dihapus"
    }
@router.get("/attendance/export-pdf/{course_kode}")
async def export_pdf(course_kode: str):

    pdf_path = generate_attendance_pdf(course_kode)

    if not pdf_path:
        return {
            "error": "Course tidak ditemukan"
        }

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"rekap_{course_kode}.pdf"
    )