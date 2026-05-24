const express = require('express');
const router = express.Router();
const User = require('../models/User');

// Middleware untuk mendapatkan facesCollection dari app locals
const getFacesCollection = (req, res, next) => {
  if (!req.app.locals.facesCollection) {
    return res.status(500).json({ error: 'Database faces belum siap' });
  }
  req.facesCollection = req.app.locals.facesCollection;
  next();
};

router.get('/', async (req, res) => {
  try {
    const users = await User.find().select('-password');
    res.json(users);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

// GET semua mahasiswa dengan status registrasi wajah (ada/tidak di faces)
router.get('/mahasiswa/face-status', getFacesCollection, async (req, res) => {
  try {
    const facesCollection = req.facesCollection;
    const mahasiswa = await User.find({ role: 'mahasiswa' }).select('-password');
    const result = await Promise.all(mahasiswa.map(async (user) => {
      const face = await facesCollection.findOne({ name: user.name });
      return {
        nim: user.nim_nidn,
        name: user.name,
        face_registered: !!face
      };
    }));
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE data wajah berdasarkan nama (reset registrasi)
router.delete('/faces/:name', getFacesCollection, async (req, res) => {
  try {
    const facesCollection = req.facesCollection;
    const { name } = req.params;
    const result = await facesCollection.deleteOne({ name });
    if (result.deletedCount === 0) {
      return res.status(404).json({ error: 'Data wajah tidak ditemukan' });
    }
    res.json({ message: 'Data wajah berhasil direset. Mahasiswa dapat registrasi ulang.' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;