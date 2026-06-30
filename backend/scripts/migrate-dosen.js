// scripts/migrate-gelar-dosen.js
// Jalankan: node scripts/migrate-gelar-dosen.js

require('dotenv').config();
const mongoose = require('mongoose');
const dns = require('dns');

// Set DNS untuk koneksi stabil ke Atlas
dns.setServers(['8.8.8.8', '8.8.4.4']);

const MONGODB_URI = process.env.MONGODB_URI;

async function migrateGelar() {
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

    // Ambil koneksi native driver
    const db = mongoose.connection.db;
    const usersCollection = db.collection('users');

    // ===== 1. CEK DATA DOSEN YANG BELUM PUNYA GELAR =====
    const dosenWithoutGelar = await usersCollection.find({
      role: 'dosen',
      gelar: { $exists: false }
    }).toArray();

    console.log(`📋 Menemukan ${dosenWithoutGelar.length} dosen yang belum memiliki field gelar`);

    if (dosenWithoutGelar.length === 0) {
      console.log('✅ Semua dosen sudah memiliki field gelar. Tidak perlu migrasi.');
      process.exit(0);
    }

    // Tampilkan 5 nama pertama sebagai contoh
    console.log('\n📋 Contoh dosen yang akan diupdate:');
    dosenWithoutGelar.slice(0, 5).forEach(d => {
      console.log(`   - ${d.name} (${d.nim_nidn})`);
    });
    if (dosenWithoutGelar.length > 5) {
      console.log(`   ... dan ${dosenWithoutGelar.length - 5} lainnya`);
    }

    // ===== 2. KONFIRMASI (opsional, comment jika ingin auto-run) =====
    // Jika ingin auto-run tanpa konfirmasi, hapus/comment bagian ini
    console.log('\n⚠️  Akan menambahkan field gelar dengan nilai kosong ("") untuk semua dosen di atas.');
    console.log('   Tekan Ctrl+C untuk membatalkan, atau tunggu 5 detik untuk melanjutkan...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    // ===== 3. UPDATE DATA =====
    console.log('\n🔄 Memperbarui data dosen...');
    const result = await usersCollection.updateMany(
      {
        role: 'dosen',
        gelar: { $exists: false }
      },
      {
        $set: { gelar: '' }
      }
    );

    console.log(`✅ Berhasil mengupdate ${result.modifiedCount} dosen`);
    console.log(`📊 Total dokumen yang cocok: ${result.matchedCount}`);

    // ===== 4. VERIFIKASI =====
    const afterCount = await usersCollection.countDocuments({
      role: 'dosen',
      gelar: { $exists: false }
    });
    console.log(`📊 Sisa dosen tanpa gelar: ${afterCount}`);

    if (afterCount === 0) {
      console.log('🎉 Migrasi selesai! Semua dosen sudah memiliki field gelar.');
    } else {
      console.log(`⚠️ Masih ada ${afterCount} dosen yang belum terupdate. Periksa kembali.`);
    }

    process.exit(0);

  } catch (error) {
    console.error('❌ Error migrasi:', error);
    process.exit(1);
  }
}

migrateGelar();