const mongoose = require('mongoose');

const courseSchema = new mongoose.Schema({
  kode_mk: {
    type: String,
    required: true,
    unique: true
  },

  nama_mk: {
    type: String,
    required: true
  },
  sks: {
  type: Number,
  required: true,
  min: 1,
  max: 6,
  default: 2
  },
  prodi: {
    type: String,
    enum: ['Informatika', 'Elektro', 'Manajemen'],
    required: true
  },

  semester: {
    type: Number,
    required: true,
    min: 1,
    max: 8
  },

  dosen_pengampu: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },

  hari: {
    type: String,
    required: true
  },

  jam_mulai: {
    type: String,
    required: true
  },

  jam_selesai: {
    type: String,
    required: true
  },
  late_tolerance_minutes: {
    type: Number,
    default: 15,   // toleransi default 15 menit
    min: 0
  },
  ruangan: {
    type: String,
    required: true
  }

}, {
  timestamps: true
});

module.exports = mongoose.model('Course', courseSchema);