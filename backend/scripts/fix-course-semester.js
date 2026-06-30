// scripts/fix-course-semester.js
require('dotenv').config();
const mongoose = require('mongoose');
const dns = require('dns');
dns.setServers(['8.8.8.8', '8.8.4.4']);

const Course = require('../models/course');
const { getCurrentAcademicPeriod } = require('../utils/academicHelper');

async function fixCourses() {
  try {
    await mongoose.connect(process.env.MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
    });
    console.log('✅ Terhubung ke MongoDB');

    const { tahun_ajaran, jenis_semester } = getCurrentAcademicPeriod();
    console.log(`📅 Periode yang benar untuk saat ini: ${tahun_ajaran} - ${jenis_semester}`);

    // Update semua course ke periode yang benar
    const result = await Course.updateMany(
      {},
      { $set: { tahun_ajaran, jenis_semester } }
    );
    console.log(`✅ Course diperbaiki: ${result.modifiedCount} dokumen terupdate`);

    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

fixCourses();