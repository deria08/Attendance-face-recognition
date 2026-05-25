const mongoose = require('mongoose');
const Course = require('../models/course');
const User = require('../models/user');


// ================= CREATE COURSE =================
exports.createCourse = async (req, res) => {
  try {

    const {
      kode_mk,
      nama_mk,
      prodi,
      semester,
      dosen_pengampu,
      hari,
      jam_mulai,
      jam_selesai,
      ruangan,
      late_tolerance_minutes, // ← tambahkan
      sks                    // ← tambahkan
    } = req.body;

    if (
      !kode_mk ||
      !nama_mk ||
      !prodi ||
      !semester ||
      !dosen_pengampu ||
      !hari ||
      !jam_mulai ||
      !jam_selesai ||
      !ruangan
    ) {
      return res.status(400).json({
        message: 'Data mata kuliah tidak lengkap'
      });
    }

    // cek dosen
    const dosen = await User.findById(dosen_pengampu);

    if (!dosen || dosen.role !== 'dosen') {
      return res.status(400).json({
        message: 'Dosen pengampu tidak valid'
      });
    }

    // cek kode mk
    const existing = await Course.findOne({ kode_mk });

    if (existing) {
      return res.status(400).json({
        message: 'Kode mata kuliah sudah digunakan'
      });
    }

    const course = new Course({
      kode_mk,
      nama_mk,
      prodi,
      semester,
      dosen_pengampu,
      hari,
      jam_mulai,
      jam_selesai,
      ruangan,
      late_tolerance_minutes: late_tolerance_minutes || 15,
      sks: sks || 2
    });

    await course.save();

    res.json({
      message: 'Mata kuliah berhasil dibuat',
      course
    });

  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: 'Server error'
    });
  }
};


// ================= GET ALL COURSES =================
exports.getAllCourses = async (req, res) => {
  try {

    const courses = await Course.find()
      .populate('dosen_pengampu', 'name nim_nidn email');

    res.json(courses);

  } catch (error) {
    res.status(500).json({
      message: 'Server error'
    });
  }
};


// ================= GET COURSE BY ID =================
exports.getCourseById = async (req, res) => {
  try {

    const course = await Course.findById(req.params.id)
      .populate('dosen_pengampu', 'name nim_nidn email');

    if (!course) {
      return res.status(404).json({
        message: 'Mata kuliah tidak ditemukan'
      });
    }

    res.json(course);

  } catch (error) {
    res.status(500).json({
      message: 'Server error'
    });
  }
};


// ================= GET COURSE BY DOSEN =================
exports.getCoursesByDosen = async (req, res) => {
  try {
    const { dosenId } = req.params;
    let user;
    // Coba cari sebagai ObjectId
    if (mongoose.Types.ObjectId.isValid(dosenId)) {
      user = await User.findById(dosenId);
    }
    // Jika tidak ketemu, cari berdasarkan nim_nidn
    if (!user) {
      user = await User.findOne({ nim_nidn: dosenId, role: 'dosen' });
    }
    if (!user) {
      return res.status(404).json({ message: 'Dosen tidak ditemukan' });
    }
    const courses = await Course.find({ dosen_pengampu: user._id }).populate('dosen_pengampu', 'name');
    res.json(courses);
  } catch (error) {
    console.error('Error in getCoursesByDosen:', error);
    res.status(500).json({ message: 'Server error' });
  }
};


// ================= GET COURSE BY PRODI =================
exports.getCoursesByProdi = async (req, res) => {
  try {

    const courses = await Course.find({
      prodi: req.params.prodi
    }).populate('dosen_pengampu', 'name');

    res.json(courses);

  } catch (error) {
    res.status(500).json({
      message: 'Server error'
    });
  }
};


// ================= UPDATE COURSE =================
exports.updateCourse = async (req, res) => {
  try {

    const updateData = req.body;

    // validasi dosen jika diubah
    if (updateData.dosen_pengampu) {

      const dosen = await User.findById(updateData.dosen_pengampu);

      if (!dosen || dosen.role !== 'dosen') {
        return res.status(400).json({
          message: 'Dosen pengampu tidak valid'
        });
      }
    }

    const course = await Course.findByIdAndUpdate(
      req.params.id,
      updateData,
      { new: true }
    ).populate('dosen_pengampu', 'name');

    if (!course) {
      return res.status(404).json({
        message: 'Mata kuliah tidak ditemukan'
      });
    }

    res.json({
      message: 'Mata kuliah berhasil diupdate',
      course
    });

  } catch (error) {
    console.error(error);

    res.status(500).json({
      message: 'Server error'
    });
  }
};


// ================= DELETE COURSE =================
exports.deleteCourse = async (req, res) => {
  try {

    const course = await Course.findByIdAndDelete(req.params.id);

    if (!course) {
      return res.status(404).json({
        message: 'Mata kuliah tidak ditemukan'
      });
    }

    res.json({
      message: 'Mata kuliah berhasil dihapus'
    });

  } catch (error) {
    res.status(500).json({
      message: 'Server error'
    });
  }
};

exports.getAvailableCourses = async (req, res) => {
  try {
    const { prodi, semester } = req.query;
    if (!prodi || !semester) {
      return res.status(400).json({ message: 'Prodi dan semester diperlukan' });
    }
    const courses = await Course.find({
      prodi: prodi,
      semester: parseInt(semester)
    }).populate('dosen_pengampu', 'name');
    res.json(courses);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};