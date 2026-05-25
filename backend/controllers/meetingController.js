const Meeting = require('../models/meeting');
const Course = require('../models/course');
const User = require('../models/user');

// Buka sesi absensi
exports.openMeeting = async (req, res) => {
  try {
    const { course_id, pertemuan_ke } = req.body;
    console.log('Request body:', req.body);

    if (!course_id || !pertemuan_ke) {
      return res.status(400).json({ message: 'course_id dan pertemuan_ke wajib diisi' });
    }

    if (!req.user) {
      return res.status(401).json({ message: 'Unauthorized: No user in token' });
    }
    const dosen_id = req.user.id;
    console.log('Dosen ID from token:', dosen_id);

    const course = await Course.findById(course_id);
    if (!course) {
      return res.status(404).json({ message: 'Mata kuliah tidak ditemukan' });
    }

    // ✅ Perbaiki: cek status 'active'
    const active = await Meeting.findOne({ course_id, status: 'active' });
    if (active) {
      return res.status(400).json({ message: 'Masih ada sesi aktif untuk mata kuliah ini' });
    }

    // ✅ Perbaiki: gunakan status 'active'
    const meeting = new Meeting({
      course_id,
      pertemuan_ke,
      opened_by: dosen_id,
      start_time: new Date(),
      status: 'active'   // <-- ganti is_open
    });
    await meeting.save();

    res.status(201).json({ message: 'Sesi absensi dibuka', meeting });
  } catch (error) {
    console.error('Error in openMeeting:', error);
    res.status(500).json({ message: 'Server error', error: error.message });
  }
};

// Tutup sesi
exports.closeMeeting = async (req, res) => {
  try {
    const meeting = await Meeting.findById(req.params.id);
    if (!meeting) return res.status(404).json({ message: 'Sesi tidak ditemukan' });
    
    // ✅ Perbaiki: ubah status menjadi 'closed'
    meeting.status = 'closed';
    meeting.end_time = new Date();
    await meeting.save();
    
    res.json({ message: 'Sesi ditutup', meeting });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error' });
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