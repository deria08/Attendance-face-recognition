const mongoose = require('mongoose');

const courseSchema = new mongoose.Schema({
  kode_mk: { type: String, required: true, unique: true },
  nama_mk: { type: String, required: true },
  sks: { type: Number, required: true, min: 1, max: 6, default: 2 },
  prodi: { type: String, enum: ['Informatika', 'Elektro'], required: true },
  semester: { type: Number, required: true, min: 1, max: 8 },
  dosen_pengampu: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  hari: { type: String, required: true },
  jam_mulai: { type: String, required: true },
  jam_selesai: { type: String, required: true },
  late_tolerance_minutes: { type: Number, default: 15, min: 0 },
  ruangan: { type: String, required: true },

  // ⭐ PERUBAHAN: Tambahkan field tahun ajaran dan jenis semester
  tahun_ajaran: { type: String, required: true }, // contoh: "2024/2025"
  jenis_semester: { type: String, enum: ['ganjil', 'genap'], required: true }

}, { timestamps: true });

module.exports = mongoose.model('Course', courseSchema);