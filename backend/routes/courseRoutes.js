const express = require('express');
const router = express.Router();
const { verifyToken, requireRole } = require('../middleware/authMiddleware'); // sesuaikan path

const {
  createCourse,
  getAllCourses,
  getCourseById,
  getCoursesByDosen,
  getCoursesByProdi,
  updateCourse,
  deleteCourse,
  getAvailableCourses
} = require('../controllers/courseController');

// Semua route di bawah ini memerlukan token valid
router.use(verifyToken);

// CREATE - hanya admin
router.post('/', requireRole(['admin']), createCourse);

// READ ALL - admin dan dosen
router.get('/', requireRole(['admin', 'dosen']), getAllCourses);

// READ BY ID - admin dan dosen
router.get('/:id', requireRole(['admin', 'dosen']), getCourseById);

// READ BY DOSEN - admin dan dosen (dosen bisa melihat miliknya)
router.get('/dosen/:dosenId', requireRole(['admin', 'dosen']), getCoursesByDosen);

// READ BY PRODI - admin dan dosen
router.get('/prodi/:prodi', requireRole(['admin', 'dosen']), getCoursesByProdi);

// UPDATE - hanya admin
router.put('/:id', requireRole(['admin']), updateCourse);

// DELETE - hanya admin
router.delete('/:id', requireRole(['admin']), deleteCourse);

// AVAILABLE - untuk semua role (termasuk mahasiswa)
router.get('/available', requireRole(['admin', 'dosen', 'mahasiswa']), getAvailableCourses);

module.exports = router;