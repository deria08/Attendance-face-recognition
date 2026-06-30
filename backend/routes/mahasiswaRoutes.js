const express = require('express');
const router = express.Router();
const User = require('../models/user');
const { ObjectId } = require('mongodb');

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

router.get('/mahasiswa/face-status', getFacesCollection, async (req, res) => {
  try {
    const facesCollection = req.facesCollection;
    const mahasiswa = await User.find({ role: 'mahasiswa' }).select('-password');
    const result = await Promise.all(mahasiswa.map(async (user) => {
      const face = await facesCollection.findOne({ user_id: user._id });
      return {
        nim: user.nim_nidn,
        name: user.name,
        face_registered: !!face
      };
    }));
    res.json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

router.delete('/faces/:id', getFacesCollection, async (req, res) => {
  try {
    const facesCollection = req.facesCollection;
    const { id } = req.params;

    let userId = null;

    if (ObjectId.isValid(id)) {
      const user = await User.findById(id);
      if (user && user.role === 'mahasiswa') {
        userId = user._id;
      }
    }

    if (!userId) {
      const user = await User.findOne({ nim_nidn: id, role: 'mahasiswa' });
      if (user) {
        userId = user._id;
      }
    }

    if (!userId) {
      return res.status(404).json({ error: 'Mahasiswa tidak ditemukan' });
    }

    const result = await facesCollection.deleteOne({ user_id: userId });
    if (result.deletedCount === 0) {
      return res.status(404).json({ error: 'Data wajah tidak ditemukan' });
    }

    res.json({ message: 'Data wajah berhasil dihapus' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;