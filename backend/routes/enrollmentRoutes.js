const express = require('express');
const router = express.Router();
const { verifyToken, requireRole } = require('../middleware/authMiddleware');
const enrollmentController = require('../controllers/enrollmentController'); // ✅ import

// Semua route memerlukan token
router.use(verifyToken);

// --- Existing routes ---
router.post('/', requireRole(['admin']), enrollmentController.enrollMahasiswa);
router.get('/', requireRole(['admin']), enrollmentController.getAllEnrollments);
router.get('/mahasiswa/:mahasiswaId', requireRole(['admin', 'mahasiswa']), enrollmentController.getCoursesByMahasiswa);
router.get('/course/:courseId', requireRole(['admin', 'dosen']), enrollmentController.getMahasiswaByCourse);
router.delete('/:id', requireRole(['admin']), enrollmentController.deleteEnrollment);

// --- Import routes ---
router.get('/template', requireRole(['admin']), enrollmentController.downloadTemplate);
router.post(
    '/import',
    requireRole(['admin']),
    enrollmentController.uploadMiddleware,
    enrollmentController.importEnrollments
);
router.post('/import/export-errors', requireRole(['admin']), enrollmentController.downloadValidationResult);

module.exports = router;