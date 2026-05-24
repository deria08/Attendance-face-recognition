const mongoose = require('mongoose');

const meetingSchema = new mongoose.Schema({
  course_id: { 
    type: mongoose.Schema.Types.ObjectId, 
    ref: 'Course', 
    required: true 
  },
  pertemuan_ke: { 
    type: Number, 
    required: true, 
    min: 1, 
    max: 16 
  },
  opened_by: { 
    type: mongoose.Schema.Types.ObjectId, 
    ref: 'User', 
    required: true 
  },
  start_time: { 
    type: Date, default: Date.now },
  end_time: { 
    type: Date 
  },
  status: { 
    type: String, 
    enum: ['active', 'closed', 'cancelled'], 
    default: 'active' 
  }
}, { timestamps: true });
// Hapus field is_open, ganti dengan status

module.exports = mongoose.model('Meeting', meetingSchema);