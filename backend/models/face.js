const mongoose = require('mongoose');

const faceSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },

  nim: {
    type: String,
    required: true
  },

  imageUrl: {
    type: String
  },

  embedding: {
    type: [Number],   // 🔥 penting untuk AI
    default: []
  },

  createdAt: {
    type: Date,
    default: Date.now
  }
});