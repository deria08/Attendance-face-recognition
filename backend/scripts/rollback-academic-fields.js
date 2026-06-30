// scripts/rollback-academic-fields.js
// Jalankan: node scripts/rollback-academic-fields.js

require('dotenv').config();
const mongoose = require('mongoose');
const dns = require('dns');

// Set DNS untuk koneksi stabil ke Atlas
dns.setServers(['8.8.8.8', '8.8.4.4']);

const MONGODB_URI = process.env.MONGODB_URI;

async function rollback() {
  if (!MONGODB_URI) {
    console.error('❌ MONGODB_URI tidak ditemukan di .env');
    process.exit(1);
  }

  try {
    console.log('🔄 Menghubungkan ke MongoDB...');
    await mongoose.connect(MONGODB_URI, {
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 60000,
    });
    console.log('✅ Terhubung ke MongoDB');

    // Ambil koneksi native driver untuk operasi index
    const db = mongoose.connection.db;

    // ==================== 1. HAPUS FIELD DI ENROLLMENTS ====================
    console.log('📋 Menghapus field tahun_ajaran & jenis_semester dari enrollments...');
    const enrollResult = await db.collection('enrollments').updateMany(
      {},
      { $unset: { tahun_ajaran: "", jenis_semester: "" } }
    );
    console.log(`✅ Enrollments diupdate: ${enrollResult.modifiedCount} dokumen`);

    // ==================== 2. HAPUS FIELD DI MEETINGS ====================
    console.log('📋 Menghapus field tahun_ajaran & jenis_semester dari meetings...');
    const meetResult = await db.collection('meetings').updateMany(
      {},
      { $unset: { tahun_ajaran: "", jenis_semester: "" } }
    );
    console.log(`✅ Meetings diupdate: ${meetResult.modifiedCount} dokumen`);

    // ==================== 3. HAPUS INDEX BARU (4 FIELD) DI ENROLLMENTS ====================
    // Cari index yang mengandung field tahun_ajaran dan jenis_semester
    const indexes = await db.collection('enrollments').indexes();
    const indexToDrop = indexes.find(idx => 
      idx.key && idx.key.tahun_ajaran && idx.key.jenis_semester
    );

    if (indexToDrop) {
      console.log(`🗑️ Menghapus index baru: ${indexToDrop.name}`);
      await db.collection('enrollments').dropIndex(indexToDrop.name);
      console.log('✅ Index baru dihapus');
    } else {
      console.log('ℹ️ Tidak ditemukan index baru (mungkin sudah dihapus)');
    }

    // ==================== 4. PASTIKAN INDEX LAMA (2 FIELD) ADA ====================
    const existingIndex = indexes.find(idx => 
      idx.key && idx.key.mahasiswa && idx.key.course && !idx.key.tahun_ajaran
    );

    if (!existingIndex) {
      console.log('🔄 Membuat ulang index unik (mahasiswa + course)...');
      await db.collection('enrollments').createIndex(
        { mahasiswa: 1, course: 1 },
        { unique: true, name: 'unique_mahasiswa_course' }
      );
      console.log('✅ Index unik berhasil dibuat');
    } else {
      console.log('ℹ️ Index unik (mahasiswa + course) sudah ada');
    }

    // ==================== 5. HAPUS INDEX DI MEETINGS (jika ada) ====================
    const meetIndexes = await db.collection('meetings').indexes();
    const meetIndexToDrop = meetIndexes.find(idx =>
      idx.key && idx.key.tahun_ajaran && idx.key.jenis_semester
    );
    if (meetIndexToDrop) {
      console.log(`🗑️ Menghapus index di meetings: ${meetIndexToDrop.name}`);
      await db.collection('meetings').dropIndex(meetIndexToDrop.name);
      console.log('✅ Index meetings dihapus');
    } else {
      console.log('ℹ️ Tidak ada index tambahan di meetings');
    }

    console.log('🎉 Rollback selesai! Field dan index berhasil dikembalikan.');
    process.exit(0);

  } catch (error) {
    console.error('❌ Error rollback:', error);
    process.exit(1);
  }
}

rollback();