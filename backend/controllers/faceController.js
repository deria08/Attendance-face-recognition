const Face = require('../models/face');
const cloudinary = require('../config/cloudinary');


// ================= CREATE =================
exports.registerFace = async (req, res) => {
  try {
    const { userId } = req.body;

    if (!userId || !req.file) {
      return res.status(400).json({ message: 'Data tidak lengkap' });
    }

    // Upload ke cloudinary
    const base64 = req.file.buffer.toString('base64');
    const dataURI = `data:${req.file.mimetype};base64,${base64}`;
    const result = await cloudinary.uploader.upload(dataURI, {
      folder: 'face-recognition'
    });

    // Simpan atau update (upsert) tanpa embedding
    const face = await Face.findOneAndUpdate(
      { userId },
      { imageUrl: result.secure_url },
      { upsert: true, new: true }
    );

    res.json({
      message: 'Wajah berhasil disimpan',
      data: face
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: error.message });
  }
};

// ================= READ ALL =================
exports.getAllFaces = async (req, res) => {
  try {
    const faces = await Face.find().populate('userId', 'name nim_nidn');
    res.json(faces);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

// ================= READ BY USER =================
exports.getFaceByUserId = async (req, res) => {
  try {
    const face = await Face.findOne({ userId: req.params.userId }).populate('userId', 'name');
    if (!face) return res.status(404).json({ message: 'Data wajah tidak ditemukan' });
    res.json(face);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};

// ================= UPDATE (ganti wajah) =================
exports.updateFace = async (req, res) => {
  try {
    const { userId } = req.params;
    if (!req.file) return res.status(400).json({ message: 'File wajah wajib diupload' });

    const base64 = req.file.buffer.toString('base64');
    const dataURI = `data:${req.file.mimetype};base64,${base64}`;
    const result = await cloudinary.uploader.upload(dataURI, {
      folder: 'face-recognition'
    });

    const face = await Face.findOneAndUpdate(
      { userId },
      { imageUrl: result.secure_url },
      { new: true }
    );
    if (!face) return res.status(404).json({ message: 'Data wajah tidak ditemukan' });
    res.json({ message: 'Wajah berhasil diperbarui', data: face });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// ================= DELETE =================
exports.deleteFace = async (req, res) => {
  try {
    const { userId } = req.params;

    console.log("DELETE FACE DIPANGGIL");
    console.log("userId =", userId);

    const data = await Face.find();

    console.log("ISI COLLECTION:");
    console.log(data);

    const face = await Face.findOneAndDelete({
      userId
    });

    console.log("HASIL DELETE:", face);

    if (!face) {
      return res.status(404).json({
        message: "Data wajah tidak ditemukan"
      });
    }

    res.json({
      message: "Berhasil"
    });

  } catch(err){
    console.log(err);
  }
}

// HAPUS fungsi verifyFace karena tidak dipakai