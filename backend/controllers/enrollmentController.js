const Enrollment = require('../models/Enrollment');
const User = require('../models/User');
const Course = require('../models/Course');


// ================= ENROLL MAHASISWA =================
exports.enrollMahasiswa = async (req, res) => {
  try {

    const {
      mahasiswaId,
      courseId
    } = req.body;

    if (!mahasiswaId || !courseId) {
      return res.status(400).json({
        message: 'Data tidak lengkap'
      });
    }

    // cek mahasiswa
    const mahasiswa = await User.findById(mahasiswaId);

    if (!mahasiswa || mahasiswa.role !== 'mahasiswa') {
      return res.status(400).json({
        message: 'Mahasiswa tidak valid'
      });
    }

    // cek course
    const course = await Course.findById(courseId);

    if (!course) {
      return res.status(404).json({
        message: 'Course tidak ditemukan'
      });
    }

    // validasi prodi
    if (mahasiswa.prodi !== course.prodi) {
      return res.status(400).json({
        message: 'Prodi mahasiswa tidak sesuai dengan mata kuliah'
      });
    }

    // validasi semester
    if (mahasiswa.semester !== course.semester) {
      return res.status(400).json({
        message: 'Semester mahasiswa tidak sesuai'
      });
    }

    // cek enrollment duplicate
    const existing = await Enrollment.findOne({
      mahasiswa: mahasiswaId,
      course: courseId
    });

    if (existing) {
      return res.status(400).json({
        message: 'Mahasiswa sudah terdaftar di mata kuliah ini'
      });
    }

    const enrollment = new Enrollment({
      mahasiswa: mahasiswaId,
      course: courseId
    });

    await enrollment.save();

    res.json({
      message: 'Mahasiswa berhasil didaftarkan ke mata kuliah',
      enrollment
    });

  } catch (error) {

    console.error(error);

    res.status(500).json({
      message: 'Server error'
    });
  }
};



// ================= GET ALL ENROLLMENTS =================
exports.getAllEnrollments = async (req, res) => {
  try {

    const enrollments = await Enrollment.find()
      .populate('mahasiswa', 'name nim_nidn prodi semester')
      .populate('course');

    res.json(enrollments);

  } catch (error) {

    res.status(500).json({
      message: 'Server error'
    });
  }
};



// ================= GET COURSE MAHASISWA =================
exports.getCoursesByMahasiswa = async (req, res) => {
  if (req.user.role === 'mahasiswa' && req.user.id !== req.params.mahasiswaId) {
    return res.status(403).json({ message: 'Forbidden: Anda hanya bisa melihat data sendiri' });
  }

  try {

    const enrollments = await Enrollment.find({
      mahasiswa: req.params.mahasiswaId
    })
      .populate('course');

    res.json(enrollments);

  } catch (error) {

    res.status(500).json({
      message: 'Server error'
    });
  }
};



// ================= GET MAHASISWA DALAM COURSE =================
exports.getMahasiswaByCourse = async (req, res) => {
  try {

    const enrollments = await Enrollment.find({
      course: req.params.courseId
    })
      .populate(
        'mahasiswa',
        'name nim_nidn prodi semester'
      );

    res.json(enrollments);

  } catch (error) {

    res.status(500).json({
      message: 'Server error'
    });
  }
};

// GET enrollments by course
// exports.getEnrollmentsByCourse = async (req, res) => {
//   try {
//     const enrollments = await Enrollment.find({ course: req.params.courseId })
//       .populate('mahasiswa', 'name nim_nidn email prodi semester');
//     res.json(enrollments);
//   } catch (error) {
//     res.status(500).json({ message: 'Server error' });
//   }
// };

// ================= DELETE ENROLLMENT =================
exports.deleteEnrollment = async (req, res) => {
  try {

    const enrollment = await Enrollment.findByIdAndDelete(
      req.params.id
    );

    if (!enrollment) {
      return res.status(404).json({
        message: 'Enrollment tidak ditemukan'
      });
    }

    res.json({
      message: 'Enrollment berhasil dihapus'
    });

  } catch (error) {

    res.status(500).json({
      message: 'Server error'
    });
  }
};