from datetime import datetime, timedelta
from config.database import attendance_collection
from bson import ObjectId
import asyncio

def has_attended_today(user_id, course_id, pertemuan):
    """Check if student already attended today for given course and meeting"""
    now = datetime.now()
    start_day = datetime(now.year, now.month, now.day)
    end_day = start_day + timedelta(days=1)
    query = {
        "user_id": user_id,
        "course_id": course_id,
        "pertemuan": pertemuan,
        "status": {"$in": ["success", "late", "manual"]},
        "timestamp": {"$gte": start_day, "$lt": end_day}
    }
    existing = attendance_collection.find_one(query)
    if existing:
        print(f"⚠️ Sudah absen: {existing}")
    else:
        print("✅ Belum absen hari ini")
    return existing is not None

def has_attended_today_course(user_id, course_id):
    now = datetime.now()
    start_day = datetime(now.year, now.month, now.day)
    end_day = start_day + timedelta(days=1)
    query = {
        "user_id": user_id,
        "course_id": course_id,
        "status": {"$in": ["success", "late", "manual"]},
        "timestamp": {"$gte": start_day, "$lt": end_day}
    }
    existing = attendance_collection.find_one(query)
    return existing is not None

async def save_attendance_log(user_id, course_id, meeting_id, pertemuan, status, similarity, message, lat=None, lon=None):
    doc = {
        "user_id": user_id,
        "course_id": course_id,
        "meeting_id": meeting_id,
        "pertemuan": pertemuan,
        "timestamp": datetime.now(),
        "status": status,
        "similarity": float(similarity),
        "message": message
    }
    if lat is not None and lon is not None:
        doc["location"] = {"lat": lat, "lon": lon}
    try:
        result = await asyncio.to_thread(attendance_collection.insert_one, doc)
        print(f"✅ Saved attendance: {result.inserted_id}")
        return result
    except Exception as e:
        print(f"❌ Error saving attendance: {e}")
        raise

async def has_attended_meeting(user_id, course_id, pertemuan):
    """Check if student already attended a specific meeting (no date restriction)"""
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    if isinstance(course_id, str):
        course_id = ObjectId(course_id)

    query = {
        "user_id": user_id,
        "course_id": course_id,
        "pertemuan": pertemuan,
        "status": {"$in": ["success", "late", "manual"]}
    }
    existing = await asyncio.to_thread(attendance_collection.find_one, query)
    return existing is not None
# ===== FUNGSI UNTUK GET DAN UPDATE RECORD =====

async def get_attendance_record(user_id, course_id, pertemuan):
    """Ambil record absensi yang sudah ada (jika ada)"""
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    if isinstance(course_id, str):
        course_id = ObjectId(course_id)

    query = {
        "user_id": user_id,
        "course_id": course_id,
        "pertemuan": pertemuan,
        "status": {"$in": ["success", "late", "manual"]}
    }
    return await asyncio.to_thread(attendance_collection.find_one, query)

async def update_attendance_log(record_id, status, similarity, message, meeting_id=None, lat=None, lon=None):
    """Update record absensi yang sudah ada"""
    if isinstance(record_id, str):
        record_id = ObjectId(record_id)
    update_data = {
        "status": status,
        "similarity": float(similarity),
        "message": message,
        "timestamp": datetime.now()
    }
    if meeting_id:
        if isinstance(meeting_id, str):
            meeting_id = ObjectId(meeting_id)
        update_data["meeting_id"] = meeting_id
    if lat is not None and lon is not None:
        update_data["location"] = {"lat": lat, "lon": lon}
    
    result = await asyncio.to_thread(
        attendance_collection.update_one,
        {"_id": record_id},
        {"$set": update_data}
    )
    return result