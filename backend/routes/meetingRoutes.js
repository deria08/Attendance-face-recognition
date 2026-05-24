const express = require('express');
const router = express.Router();
const { verifyToken, requireRole } = require('../middleware/authMiddleware');
const meetingController = require('../controllers/meetingController');

// Semua route di bawah ini memerlukan token valid
router.use(verifyToken);

// Buka sesi absensi - hanya dosen dan admin
router.post('/open', requireRole(['dosen', 'admin']), meetingController.openMeeting);

// Tutup sesi - hanya dosen dan admin
router.put('/close/:id', requireRole(['dosen', 'admin']), meetingController.closeMeeting);

// Cek meeting aktif - semua role (mahasiswa, dosen, admin)
router.get('/active/:course_id', requireRole(['mahasiswa', 'dosen', 'admin']), meetingController.getActiveMeeting);

// Riwayat meeting suatu course - dosen dan admin
router.get('/course/:course_id', requireRole(['dosen', 'admin']), meetingController.getMeetingsByCourse);

module.exports = router;