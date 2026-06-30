// scripts/migrate-academic-periods.js
require('dotenv').config();
const mongoose = require('mongoose');
const dns = require('dns');

// Set DNS server ke Google DNS untuk mengatasi resolusi
dns.setServers(['8.8.8.8', '8.8.4.4']);

const Course = require('../models/course');
const Enrollment = require('../models/enrollment');
const Meeting = require('../models/meeting');
const { getCurrentAcademicPeriod } = require('../utils/academicHelper');

const MONGODB_URI = process.env.MONGODB_URI;

async function migrate() {
  if (!MONGODB_URI) {
    console.error('❌ MONGODB_URI tidak ditemukan di .env');
    process.exit(1);
  }

  try {
    // ⭐ Koneksi tanpa opsi deprecated, tambahkan timeout
    await mongoose.connect(MONGODB_URI, {
      serverSelectionTimeoutMS: 15000, // 15 detik
    });
    console.log('✅ Terhubung ke MongoDB');

    const defaultPeriod = getCurrentAcademicPeriod();
    console.log(`📅 Default periode untuk data lama: ${defaultPeriod.tahun_ajaran} - ${defaultPeriod.jenis_semester}`);

    // ================== 1. MIGRASI COURSE ==================
    const courseResult = await Course.updateMany(
      { tahun_ajaran: { $exists: false } },
      { 
        $set: {
          tahun_ajaran: defaultPeriod.tahun_ajaran,
          jenis_semester: defaultPeriod.jenis_semester
        }
      }
    );
    console.log(`✅ Course updated: ${courseResult.modifiedCount} dokumen`);

    // ================== 2. MIGRASI ENROLLMENT ==================
    const enrollmentsToUpdate = await Enrollment.find({
      tahun_ajaran: { $exists: false }
    }).populate('course');

    console.log(`📋 Menemukan ${enrollmentsToUpdate.length} enrollment yang perlu dimigrasi`);
    let enrolledUpdated = 0;
    for (const enroll of enrollmentsToUpdate) {
      if (enroll.course) {
        await Enrollment.updateOne(
          { _id: enroll._id },
          {
            $set: {
              tahun_ajaran: enroll.course.tahun_ajaran || defaultPeriod.tahun_ajaran,
              jenis_semester: enroll.course.jenis_semester || defaultPeriod.jenis_semester
            }
          }
        );
        enrolledUpdated++;
      } else {
        await Enrollment.updateOne(
          { _id: enroll._id },
          {
            $set: {
              tahun_ajaran: defaultPeriod.tahun_ajaran,
              jenis_semester: defaultPeriod.jenis_semester
            }
          }
        );
        enrolledUpdated++;
      }
    }
    console.log(`✅ Enrollment updated: ${enrolledUpdated} dokumen`);

    // ================== 3. MIGRASI MEETING ==================
    const meetingsToUpdate = await Meeting.find({
      tahun_ajaran: { $exists: false }
    }).populate('course_id');

    console.log(`📋 Menemukan ${meetingsToUpdate.length} meeting yang perlu dimigrasi`);
    let meetingUpdated = 0;
    for (const meet of meetingsToUpdate) {
      if (meet.course_id) {
        await Meeting.updateOne(
          { _id: meet._id },
          {
            $set: {
              tahun_ajaran: meet.course_id.tahun_ajaran || defaultPeriod.tahun_ajaran,
              jenis_semester: meet.course_id.jenis_semester || defaultPeriod.jenis_semester
            }
          }
        );
        meetingUpdated++;
      } else {
        await Meeting.updateOne(
          { _id: meet._id },
          {
            $set: {
              tahun_ajaran: defaultPeriod.tahun_ajaran,
              jenis_semester: defaultPeriod.jenis_semester
            }
          }
        );
        meetingUpdated++;
      }
    }
    console.log(`✅ Meeting updated: ${meetingUpdated} dokumen`);

    console.log('🎉 Migrasi selesai!');
    process.exit(0);

  } catch (error) {
    console.error('❌ Error migrasi:', error);
    process.exit(1);
  }
}

migrate();   