const mongoose = require('mongoose');

const faceSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  imageUrl: String, // dari Cloudinary
  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Face', faceSchema);