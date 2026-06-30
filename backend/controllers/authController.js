const bcrypt = require('bcrypt');
const User = require('../models/user');
const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'rahasia123';

// ---------- REGISTER ----------
exports.register = async (req, res) => {
  try {
    const { name, nim_nidn, email, role, prodi, semester, gelar } = req.body;

    if (!name || !nim_nidn || !role) { // email tidak wajib
      return res.status(400).json({ message: "Data tidak lengkap" });
    }

    if (role === 'mahasiswa' && !semester) {
      return res.status(400).json({ message: "Semester wajib diisi untuk mahasiswa" });
    }

    const existing = await User.findOne({ nim_nidn });
    if (existing) {
      return res.status(400).json({ message: "NIM/NIDN sudah terdaftar" });
    }

    const hashedPassword = await bcrypt.hash(nim_nidn, 10);

    const newUser = new User({
      name,
      nim_nidn,
      email: email || '', // opsional
      password: hashedPassword,
      role,
      prodi: prodi || null,
      semester: role === 'mahasiswa' ? semester : null,
      gelar: role === 'dosen' ? (gelar || '') : '' 
    });

    await newUser.save();

    res.json({
      message: "Register berhasil",
      nim_nidn,
      defaultPassword: nim_nidn
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Server error" });
  }
};

// ---------- LOGIN (menghasilkan token) ----------
exports.login = async (req, res) => {
  try {
    const { name, nim_nidn } = req.body;

    const user = await User.findOne({ name });
    if (!user) {
      return res.status(404).json({ message: "Nama tidak ditemukan" });
    }

    const match = await bcrypt.compare(nim_nidn, user.password);
    if (!match) {
      return res.status(401).json({ message: "NIM/NIDN salah" });
    }

    // Buat payload token
    const payload = {
      id: user._id,
      name: user.name,
      nim_nidn: user.nim_nidn,
      email: user.email,
      role: user.role,
      prodi: user.prodi,
      semester: user.semester,
      gelar: user.gelar || ''
    };
    const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '1d' });

    res.json({
      message: "Login berhasil",
      token,               // <-- token dikirim ke client
      user: payload
    });
  } catch (error) {
    console.error("Login error:", error); // <-- tambahkan ini
    res.status(500).json({ message: "Server error" });
  }
};

// ---------- GET ALL USERS (hanya untuk admin, lihat middleware di route) ----------
exports.getAllUsers = async (req, res) => {
  try {
    const users = await User.find().select('-password');
    res.json(users);
  } catch (error) {
    res.status(500).json({ message: "Server error" });
  }
};

// ---------- GET USER BY ID (admin atau pemilik akun) ----------
exports.getUserById = async (req, res) => {
  try {
    const userId = req.params.id;
    const currentUser = req.user; // dari middleware verifyToken

    // Cek hak akses: admin atau pemilik akun
    if (currentUser.role !== 'admin' && currentUser.id !== userId) {
      return res.status(403).json({ message: "Akses ditolak" });
    }

    const user = await User.findById(userId).select('-password');
    if (!user) {
      return res.status(404).json({ message: "User tidak ditemukan" });
    }
    res.json(user);
  } catch (error) {
    res.status(500).json({ message: "Server error" });
  }
};

// ---------- UPDATE USER (admin atau pemilik akun) ----------
exports.updateUser = async (req, res) => {
  try {
    const userId = req.params.id;
    const currentUser = req.user;

    if (currentUser.role !== 'admin' && currentUser.id !== userId) {
      return res.status(403).json({ message: "Akses ditolak" });
    }

    const { name, nim_nidn, email, role, password, prodi, semester, gelar } = req.body;

    const updateData = {
      name,
      email: email || '', // opsional
      role,
      prodi: prodi || null,
      semester: role === 'mahasiswa' ? semester : null,
      gelar: role === 'dosen' ? (gelar || '') : ''
    };

    // cek unik NIM/NIDN
    if (nim_nidn) {
      const existing = await User.findOne({
        nim_nidn,
        _id: { $ne: userId }
      });
      if (existing) {
        return res.status(400).json({ message: "NIM/NIDN sudah digunakan" });
      }
      updateData.nim_nidn = nim_nidn;
      if (!password) {
        updateData.password = await bcrypt.hash(nim_nidn, 10);
      }
    }

    if (password) {
      updateData.password = await bcrypt.hash(password, 10);
    }

    const user = await User.findByIdAndUpdate(userId, updateData, { new: true }).select('-password');
    if (!user) {
      return res.status(404).json({ message: "User tidak ditemukan" });
    }

    res.json({ message: "User berhasil diupdate", user });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: "Server error" });
  }
};

// ---------- DELETE USER (admin atau pemilik akun) ----------
exports.deleteUser = async (req, res) => {
  try {
    const userId = req.params.id;
    const currentUser = req.user;

    if (currentUser.role !== 'admin' && currentUser.id !== userId) {
      return res.status(403).json({ message: "Akses ditolak" });
    }

    const user = await User.findByIdAndDelete(userId);
    if (!user) {
      return res.status(404).json({ message: "User tidak ditemukan" });
    }
    res.json({ message: "User berhasil dihapus" });
  } catch (error) {
    res.status(500).json({ message: "Server error" });
  }
};

// ... setelah fungsi login, sebelum exports.getAllUsers

exports.getProfile = async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('-password');
    if (!user) return res.status(404).json({ message: 'User tidak ditemukan' });
    // Tambahkan face_registered dari collection faces (sama seperti di fetchUsers)
    const face = await Face.findOne({ userId: user._id });
    const userObj = user.toObject();
    userObj.face_registered = !!face;
    res.json(userObj);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
};