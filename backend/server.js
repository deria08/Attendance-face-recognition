const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dns = require('dns');
const { MongoClient } = require('mongodb');
require('dotenv').config();

const app = express();

// Set DNS servers ke Google DNS (untuk mengatasi resolusi)
dns.setServers(['8.8.8.8', '8.8.4.4']);
app.use(cors({
  origin: ['https://frontend.up.railway.app', 'http://localhost:5173']
}));
app.use(express.json({ limit: '10mb' }));

const faceRoutes = require('./routes/faceRoutes');
const authRoutes = require('./routes/authRoutes');
const mahasiswaRoutes = require('./routes/mahasiswaRoutes');
const courseRoutes = require('./routes/courseRoutes');
const enrollmentRoutes = require('./routes/enrollmentRoutes');
const meetingRoutes = require('./routes/meetingRoutes');

app.use('/api/meetings', meetingRoutes);
app.use('/api/enrollments', enrollmentRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/face', faceRoutes);
app.use('/api/users', mahasiswaRoutes);
app.use('/api/courses', courseRoutes);

let facesCollection;
// const uri = "mongodb+srv://deri123:OIGj9gU2HvSAhRr1@cluster0.nroolbp.mongodb.net/faceDB?retryWrites=true&w=majority";
const uri = process.env.MONGODB_URI;

// Koneksi untuk MongoClient (faces collection)
const mongoClient = new MongoClient(uri);
mongoClient.connect()
  .then(() => {
    const db = mongoClient.db('faceDB');
    facesCollection = db.collection('faces');
    app.locals.facesCollection = facesCollection;
    console.log('✅ Connected to MongoDB (faces) via MongoClient');
  })
  .catch(err => console.error('MongoClient connection error:', err));

// Koneksi Mongoose untuk user data (tanpa opsi deprecated)
mongoose.connect(uri)
  .then(() => console.log('Mongoose connected'))
  .catch(err => console.log('Mongoose error:', err));

app.listen(5000, () => {
  console.log('Server running on port 5000');
});