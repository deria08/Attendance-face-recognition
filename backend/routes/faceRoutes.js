const express = require('express');
const router = express.Router();
const upload = require('../config/upload');
const { verifyToken, requireRole } = require('../middleware/authMiddleware');
const { registerFace, getAllFaces, getFaceByUserId, updateFace, deleteFace } = require('../controllers/faceController');

router.use(verifyToken);

router.post('/register-face', requireRole(['admin', 'mahasiswa']), upload.single('image'), registerFace);
router.get('/faces', requireRole(['admin']), getAllFaces);
router.get('/faces/:userId', requireRole(['admin', 'mahasiswa']), getFaceByUserId);
router.put('/faces/:userId', requireRole(['admin']), upload.single('image'), updateFace);
router.delete('/faces/:userId', requireRole(['admin']), deleteFace);

module.exports = router;