// utils/academicHelper.js

function getCurrentAcademicPeriod() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1; // 1=Jan, 12=Des

  let tahun_ajaran, jenis_semester;

  // ✅ Aturan STTP yang benar:
  // Ganjil : Oktober (10) – Februari (2)
  // Genap  : April (4) – Agustus (8)
  if (month >= 10 && month <= 12) {
    // Ganjil: Okt–Des
    tahun_ajaran = `${year}/${year + 1}`;
    jenis_semester = 'ganjil';
  } else if (month >= 1 && month <= 2) {
    // Ganjil: Jan–Feb (masih tahun ajaran sebelumnya)
    tahun_ajaran = `${year - 1}/${year}`;
    jenis_semester = 'ganjil';
  } else if (month >= 4 && month <= 8) {
    // Genap: Apr–Ags
    tahun_ajaran = `${year - 1}/${year}`;
    jenis_semester = 'genap';
  } else {
    // Bulan transisi: Maret (3) dan September (9)
    // Fallback ke Genap agar tidak error
    if (month === 3) {
      tahun_ajaran = `${year - 1}/${year}`;
      jenis_semester = 'genap';
    } else { // month === 9
      tahun_ajaran = `${year - 1}/${year}`;
      jenis_semester = 'genap';
    }
  }

  return { tahun_ajaran, jenis_semester };
}

module.exports = { getCurrentAcademicPeriod };