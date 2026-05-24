# services/course_service.py
from config.database import enrollments_collection, courses_collection

async def get_courses_by_mahasiswa(mahasiswa_name, mahasiswa_nim=None):
    """
    Ambil daftar mata kuliah yang diikuti seorang mahasiswa.
    Karena di koleksi enrollments, field 'mahasiswa' adalah ObjectId.
    Kita perlu mencari user dulu berdasarkan name (atau nim) untuk mendapatkan _id.
    """
    # Cari user mahasiswa berdasarkan name (asumsi name unik)
    from config.database import db
    users_collection = db['users']
    mahasiswa = await users_collection.find_one({"name": mahasiswa_name, "role": "mahasiswa"})
    if not mahasiswa:
        return []
    # Cari enrollment
    enrolls = await enrollments_collection.find({"mahasiswa": mahasiswa['_id']}).to_list(100)
    course_ids = [e['course'] for e in enrolls]
    courses = []
    for cid in course_ids:
        course = await courses_collection.find_one({"_id": cid})
        if course:
            courses.append(course)
    return courses