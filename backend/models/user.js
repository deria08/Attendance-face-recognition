const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  name: { 
    type: String, 
    required: true 
  },

  nim_nidn: { 
    type: String, 
    unique: true, 
    required: true 
  },

  email: { 
    type: String, 
    required: true 
  },

  password: { 
    type: String, 
    required: true 
  },

  role: { 
    type: String, 
    enum: ['admin', 'dosen', 'mahasiswa'], 
    required: true 
  },

  // PRODI
  prodi: {
    type: String,
    enum: ['Informatika', 'Elektro', 'Manajemen'],
    default: null
  },

  // KHUSUS MAHASISWA
  semester: {
    type: Number,
    min: 1,
    max: 8,
    default: null
  }

});

module.exports = mongoose.model('User', userSchema);