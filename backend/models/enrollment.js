const mongoose = require('mongoose');

const enrollmentSchema = new mongoose.Schema({

  mahasiswa: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },

  course: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Course',
    required: true
  }

}, {
  timestamps: true
});


// agar mahasiswa tidak bisa mengambil course yang sama 2x
enrollmentSchema.index(
  { mahasiswa: 1, course: 1 },
  { unique: true }
);

module.exports = mongoose.model('Enrollment', enrollmentSchema);