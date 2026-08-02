const Enrollment = require('../models/enrollment');
const User = require('../models/user');
const Course = require('../models/course');
const multer = require('multer');
const XLSX = require('xlsx');
const path = require('path');
const fs = require('fs');
const mongoose = require('mongoose');

// ==================================================
// CONFIGURASI MULTER (Upload File)
// ==================================================
const storage = multer.memoryStorage();
const upload = multer({
    storage: storage,
    fileFilter: (req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        if (ext === '.xlsx' || ext === '.xls') {
            cb(null, true);
        } else {
            cb(new Error('Hanya file Excel (.xlsx, .xls) yang diperbolehkan'), false);
        }
    },
    limits: { fileSize: 5 * 1024 * 1024 } // 5MB
});
// ==================================================
// CACHE UNTUK IMPORT SESSION (In-Memory)
// ==================================================
// Untuk production, gunakan Redis
const importCache = {};

function generateImportId() {
    return `import_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

function cleanupCache() {
    const now = Date.now();
    for (const key in importCache) {
        if (importCache[key].expiresAt < now) {
            delete importCache[key];
        }
    }
}
setInterval(cleanupCache, 60000); // clean every minute

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
    // if (mahasiswa.semester !== course.semester) {
    //   return res.status(400).json({
    //     message: 'Semester mahasiswa tidak sesuai'
    //   });
    // }

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
// ===== PREVIEW =====
async function previewImport(req, res) {
    const file = req.file;
    const importId = generateImportId();

    try {
        const workbook = XLSX.read(file.buffer, { type: 'buffer' });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' });

        if (rows.length === 0) {
            return res.status(400).json({ message: 'File tidak memiliki data.' });
        }

        // Validasi header
        const expectedHeaders = ['Kode Mata Kuliah', 'NIM'];
        const headers = Object.keys(rows[0]);
        if (!expectedHeaders.every(h => headers.includes(h))) {
            return res.status(400).json({
                message: 'Format kolom tidak sesuai. Gunakan template yang disediakan.',
                expected: expectedHeaders,
                found: headers
            });
        }

        // Validasi setiap baris
        const validData = [];
        const errors = [];
        const duplicates = [];
        const duplicateFileSet = new Set();
        const total = rows.length;
        let validCount = 0;
        let duplicateCount = 0;
        let errorCount = 0;

        // Ambil semua data user dan course untuk caching (optimasi)
        const users = await User.find({ role: 'mahasiswa' }).select('_id nim_nidn name');
        const courses = await Course.find().select('_id kode_mk');

        const userMap = {};
        users.forEach(u => { userMap[u.nim_nidn] = u; });

        const courseMap = {};
        courses.forEach(c => { courseMap[c.kode_mk] = c; });

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const rowNum = i + 2; // +2 karena Excel row 1 = header
            const kodeMk = row['Kode Mata Kuliah']?.toString().trim() || '';
            const nim = row['NIM']?.toString().trim() || '';

            const errorsRow = [];

            // Validasi 1: Kolom wajib terisi
            if (!kodeMk) errorsRow.push('Kode Mata Kuliah kosong');
            if (!nim) errorsRow.push('NIM kosong');

            let course = null;
            let user = null;

            // Validasi 2: Kode MK ada
            if (kodeMk) {
                course = courseMap[kodeMk];
                if (!course) {
                    errorsRow.push(`Kode mata kuliah ${kodeMk} tidak ditemukan`);
                }
            }

            // Validasi 3: NIM terdaftar
            if (nim) {
                user = userMap[nim];
                if (!user) {
                    errorsRow.push(`Mahasiswa dengan NIM ${nim} tidak ditemukan`);
                }
            }

            // Validasi 4: Duplikat di file
            const fileKey = `${kodeMk}|${nim}`;
            if (kodeMk && nim && duplicateFileSet.has(fileKey)) {
                errorsRow.push(`Data duplikat pada file`);
            } else if (kodeMk && nim) {
                duplicateFileSet.add(fileKey);
            }

            // Validasi 5: Sudah terdaftar di DB
            let isAlreadyEnrolled = false;
            if (course && user) {
                const existing = await Enrollment.findOne({
                    mahasiswa: user._id,
                    course: course._id
                });
                if (existing) {
                    errorsRow.push('Mahasiswa sudah terdaftar pada mata kuliah ini');
                    isAlreadyEnrolled = true;
                }
            }

            const status = errorsRow.length > 0 ? 'error' : 'valid';

            if (status === 'valid' && course && user && !isAlreadyEnrolled) {
                validData.push({
                    row: i + 1,
                    courseId: course._id,
                    userId: user._id,
                    kodeMk,
                    nim,
                    name: user.name
                });
                validCount++;
            } else {
                if (isAlreadyEnrolled) {
                    duplicateCount++;
                } else {
                    errorCount++;
                }
                // Untuk preview, tampilkan error
                const entry = {
                    row: rowNum,
                    kodeMk: kodeMk || '-',
                    nim: nim || '-',
                    status,
                    errors: errorsRow.join(', ')
                };
                if (isAlreadyEnrolled) {
                    errors.push({ ...entry, status: 'duplicate' });
                } else {
                    errors.push(entry);
                }
            }
        }

        // Simpan validData ke cache
        importCache[importId] = {
            validData,
            expiresAt: Date.now() + 600000 // 10 menit
        };

        return res.json({
            importId,
            total,
            validCount,
            duplicateCount,
            errorCount,
            errors,
            validData: validData.map(d => ({
                row: d.row,
                kodeMk: d.kodeMk,
                nim: d.nim,
                name: d.name,
                status: 'valid'
            }))
        });

    } catch (error) {
        console.error('Preview import error:', error);
        return res.status(500).json({
            message: 'Gagal membaca file: ' + error.message
        });
    }
}

// ===== CONFIRM =====
async function confirmImport(req, res) {
    const { importId } = req.body;

    if (!importId || !importCache[importId]) {
        return res.status(400).json({ message: 'Session import tidak ditemukan atau expired. Silakan upload ulang.' });
    }

    const session = importCache[importId];
    const validData = session.validData;

    if (validData.length === 0) {
        delete importCache[importId];
        return res.status(400).json({ message: 'Tidak ada data valid untuk diimport.' });
    }

    let importedCount = 0;
    const failedItems = [];

    try {
        // Gunakan transaksi jika memungkinkan
        const sessionDb = await mongoose.startSession();
        sessionDb.startTransaction();

        try {
            for (const item of validData) {
                try {
                    // Cek ulang untuk menghindari race condition
                    const existing = await Enrollment.findOne({
                        mahasiswa: item.userId,
                        course: item.courseId
                    }).session(sessionDb);

                    if (!existing) {
                        const enrollment = new Enrollment({
                            mahasiswa: item.userId,
                            course: item.courseId
                        });
                        await enrollment.save({ session: sessionDb });
                        importedCount++;
                    } else {
                        failedItems.push({
                            row: item.row,
                            nim: item.nim,
                            kodeMk: item.kodeMk,
                            reason: 'Sudah terdaftar (terdeteksi saat import)'
                        });
                    }
                } catch (err) {
                    failedItems.push({
                        row: item.row,
                        nim: item.nim,
                        kodeMk: item.kodeMk,
                        reason: err.message
                    });
                }
            }

            await sessionDb.commitTransaction();
            sessionDb.endSession();

        } catch (error) {
            await sessionDb.abortTransaction();
            sessionDb.endSession();
            throw error;
        }

        // Hapus session setelah digunakan
        delete importCache[importId];

        return res.json({
            message: `Import berhasil. ${importedCount} data berhasil ditambahkan.`,
            importedCount,
            totalValid: validData.length,
            failedItems
        });

    } catch (error) {
        console.error('Confirm import error:', error);
        return res.status(500).json({
            message: 'Gagal menyimpan data: ' + error.message
        });
    }
}

// ==================================================
// EKSPOR UNTUK FITUR IMPORT
// ==================================================

// ⭐ Middleware upload (menggunakan .single('file'))
exports.uploadMiddleware = upload.single('file');

// ⭐ Handler utama import (preview & confirm)
exports.importEnrollments = async (req, res) => {
    const { action } = req.body;
    const file = req.file;

    if (!file && action !== 'confirm') {
        return res.status(400).json({ message: 'File tidak ditemukan' });
    }

    if (action === 'preview') {
        return await previewImport(req, res);
    } else if (action === 'confirm') {
        return await confirmImport(req, res);
    } else {
        return res.status(400).json({ message: 'Action tidak valid. Gunakan "preview" atau "confirm"' });
    }
};

// ⭐ Download template Excel
exports.downloadTemplate = async (req, res) => {
    try {
        const wb = XLSX.utils.book_new();
        const data = [
            ['Kode Mata Kuliah', 'NIM'],
            ['IF201', '220101'],
            ['IF201', '220102'],
            ['IF201', '220103']
        ];
        const ws = XLSX.utils.aoa_to_sheet(data);
        ws['!cols'] = [{ wch: 20 }, { wch: 15 }];
        XLSX.utils.book_append_sheet(wb, ws, 'Template');
        const buffer = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', 'attachment; filename=template_enrollment.xlsx');
        res.send(buffer);
    } catch (error) {
        console.error('Download template error:', error);
        res.status(500).json({ message: 'Gagal download template' });
    }
};

// ==================================================
// DOWNLOAD HASIL VALIDASI (Opsional)
// ==================================================
exports.downloadValidationResult = async (req, res) => {
    const { errors } = req.body;

    if (!errors || errors.length === 0) {
        return res.status(400).json({ message: 'Tidak ada error untuk diekspor.' });
    }

    try {
        const data = [
            ['Baris', 'Kode Mata Kuliah', 'NIM', 'Status', 'Error']
        ];
        errors.forEach(err => {
            data.push([
                err.row,
                err.kodeMk,
                err.nim,
                err.status || 'error',
                err.errors || err.reason || ''
            ]);
        });

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(data);
        ws['!cols'] = [{ wch: 10 }, { wch: 20 }, { wch: 15 }, { wch: 15 }, { wch: 40 }];
        XLSX.utils.book_append_sheet(wb, ws, 'Error');
        const buffer = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });

        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        res.setHeader('Content-Disposition', 'attachment; filename=hasil_validasi_import.xlsx');
        res.send(buffer);
    } catch (error) {
        console.error('Download validation result error:', error);
        res.status(500).json({ message: 'Gagal download hasil validasi' });
    }
};