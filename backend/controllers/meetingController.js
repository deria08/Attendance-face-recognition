const Meeting = require('../models/meeting');
const Course = require('../models/course');
const User = require('../models/user');
const Enrollment = require('../models/enrollment'); // import model enrollment
const mongoose = require('mongoose');


// Buka sesi absensi
exports.openMeeting = async (req, res) => {
  try {
    const { course_id, pertemuan_ke, force = false } = req.body;
    console.log('Request body:', req.body);

    if (!course_id || !pertemuan_ke) {
      return res.status(400).json({ message: 'course_id dan pertemuan_ke wajib diisi' });
    }

    if (!req.user) {
      return res.status(401).json({ message: 'Unauthorized: No user in token' });
    }
    const dosen_id = req.user.id;

    const course = await Course.findById(course_id);
    if (!course) {
      return res.status(404).json({ message: 'Mata kuliah tidak ditemukan' });
    }

    // Jika force = true, tutup semua meeting aktif untuk course ini
    if (force) {
      await Meeting.updateMany(
        { course_id, status: 'active' },
        { status: 'closed', end_time: new Date() }
      );
    } else {
      // Jika force = false, cek apakah ada meeting aktif (perilaku normal)
      const active = await Meeting.findOne({ course_id, status: 'active' });
      if (active) {
        return res.status(400).json({ message: 'Masih ada sesi aktif untuk mata kuliah ini' });
      }
    }

    // Buat meeting baru
    const meeting = new Meeting({
      course_id,
      pertemuan_ke,
      opened_by: dosen_id,
      start_time: new Date(),
      status: 'active'
    });
    await meeting.save();

    res.status(201).json({
      message: force ? 'Sesi absensi dibuka kembali' : 'Sesi absensi dibuka',
      meeting
    });
  } catch (error) {
    console.error('Error in openMeeting:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
};

// ===== FUNGSI AUTO-FILL FAILED =====
async function autoFillFailedAttendance(courseId, pertemuan, meetingId = null) {
  const db = mongoose.connection.db;
  const attendanceCollection = db.collection('attendances');
  const manualCollection = db.collection('manual_attendances');

  // Ambil semua mahasiswa yang terdaftar di course ini
  const enrollments = await Enrollment.find({ course: courseId }).populate('mahasiswa', '_id');
  const courseObjId = new mongoose.Types.ObjectId(courseId);
  const pertemuanInt = parseInt(pertemuan);

  let insertedCount = 0;

  for (const enrollment of enrollments) {
    const mahasiswaId = enrollment.mahasiswa._id;

    // Cek apakah sudah ada attendance record (baik di attendances maupun manual)
    const existing = await attendanceCollection.findOne({
      user_id: mahasiswaId,
      course_id: courseObjId,
      pertemuan: pertemuanInt
    });
    if (existing) continue;

    const existingManual = await manualCollection.findOne({
      user_id: mahasiswaId,
      course_id: courseObjId,
      pertemuan: pertemuanInt
    });
    if (existingManual) continue;

    // Buat record baru dengan status 'failed'
    const newRecord = {
      user_id: mahasiswaId,
      course_id: courseObjId,
      meeting_id: meetingId ? new mongoose.Types.ObjectId(meetingId) : null,
      pertemuan: pertemuanInt,
      timestamp: new Date(),
      status: 'failed',
      similarity: 0,
      message: 'Otomatis tidak hadir (absensi ditutup)',
      method: 'auto' // penanda bahwa ini dibuat otomatis
    };
    await attendanceCollection.insertOne(newRecord);
    insertedCount++;
  }

  return insertedCount;
}

// ===== TUTUP SESI (DENGAN AUTO-FILL) =====
exports.closeMeeting = async (req, res) => {
  try {
    const meetingId = req.params.id;
    const meeting = await Meeting.findById(meetingId);
    if (!meeting) {
      return res.status(404).json({ message: 'Sesi tidak ditemukan' });
    }

    // Cek apakah sesi sudah ditutup
    if (meeting.status === 'closed') {
      return res.status(400).json({ message: 'Sesi sudah ditutup' });
    }

    const courseId = meeting.course_id;
    const pertemuan = meeting.pertemuan_ke;

    // 1. Tutup sesi
    meeting.status = 'closed';
    meeting.end_time = new Date();
    await meeting.save();

    // 2. Auto-fill failed untuk mahasiswa yang belum absen
    const insertedCount = await autoFillFailedAttendance(courseId, pertemuan, meetingId);

    res.json({
      message: `Sesi ditutup. ${insertedCount} mahasiswa otomatis diberi status Tidak Hadir.`,
      meeting,
      insertedCount
    });
  } catch (error) {
    console.error('Error closing meeting:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
};

// Cek meeting aktif berdasarkan course_id
exports.getActiveMeeting = async (req, res) => {
  try {
    // ✅ Perbaiki: cari status 'active'
    const meeting = await Meeting.findOne({ 
      course_id: req.params.course_id, 
      status: 'active'
    }).populate('course_id', 'kode_mk nama_mk');
    if (!meeting) return res.status(404).json({ message: 'Tidak ada sesi aktif' });
    res.json(meeting);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
};

// Riwayat meeting suatu course
exports.getMeetingsByCourse = async (req, res) => {
  try {
    const meetings = await Meeting.find({ course_id: req.params.course_id }).sort({ start_time: -1 });
    res.json(meetings);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
  }
};
// ===== CEK APAKAH PERTEMUAN SUDAH MEMILIKI DATA ABSENSI =====
exports.checkAttendance = async (req, res) => {
  try {
    const { course_id, pertemuan } = req.query;
    if (!course_id || !pertemuan) {
      return res.status(400).json({ message: 'course_id dan pertemuan wajib diisi' });
    }

    const db = mongoose.connection.db;
    const attendanceCollection = db.collection('attendances');
    const manualAttendanceCollection = db.collection('manual_attendances');

    const courseIdObj = new mongoose.Types.ObjectId(course_id);
    const pertemuanInt = parseInt(pertemuan);

    const attendanceCount = await attendanceCollection.countDocuments({
      course_id: courseIdObj,
      pertemuan: pertemuanInt
    });

    const manualCount = await manualAttendanceCollection.countDocuments({
      course_id: courseIdObj,
      pertemuan: pertemuanInt
    });

    const total = attendanceCount + manualCount;

    res.json({
      hasAttendance: total > 0,
      count: total
    });
  } catch (error) {
    console.error('Error checking attendance:', error);
    res.status(500).json({ message: 'Server error' });
  }
};