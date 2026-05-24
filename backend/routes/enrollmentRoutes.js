const express = require('express');
const router = express.Router();
const { verifyToken, requireRole } = require('../middleware/authMiddleware');

const {
  enrollMahasiswa,
  getAllEnrollments,
  getCoursesByMahasiswa,
  getMahasiswaByCourse,
  deleteEnrollment,
  // getEnrollmentsByCourse
} = require('../controllers/enrollmentController');

// Semua route memerlukan token
router.use(verifyToken);

// ENROLL - hanya admin
router.post('/', requireRole(['admin']), enrollMahasiswa);

// GET ALL - hanya admin
router.get('/', requireRole(['admin']), getAllEnrollments);

// GET COURSE MAHASISWA - admin dan mahasiswa (mahasiswa hanya bisa lihat miliknya, dicek controller)
router.get('/mahasiswa/:mahasiswaId', requireRole(['admin', 'mahasiswa']), getCoursesByMahasiswa);

// GET MAHASISWA DALAM COURSE - admin dan dosen (dosen hanya bisa lihat course yang diampu)
router.get('/course/:courseId', requireRole(['admin', 'dosen']), getMahasiswaByCourse);

// DELETE - hanya admin
router.delete('/:id', requireRole(['admin']), deleteEnrollment);

// Duplicate route? Saya komentari agar tidak bentrok
// router.get('/course/:courseId', getEnrollmentsByCourse);

module.exports = router;