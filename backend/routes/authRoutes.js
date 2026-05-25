const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { verifyToken, requireRole } = require('../middleware/authMiddleware');

// Public routes (tidak perlu token)
router.post('/register', authController.register);
router.post('/login', authController.login);

// Protected routes (perlu token)
router.use(verifyToken); // semua route di bawah ini memerlukan token

router.get('/profile', authController.getProfile); // <-- tambahkan ini
router.get('/users', requireRole(['admin']), authController.getAllUsers);
router.get('/users/:id', authController.getUserById);
router.put('/users/:id', authController.updateUser);
router.delete('/users/:id', authController.deleteUser);

module.exports = router;