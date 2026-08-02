import os
import math
import json
import statistics
import requests
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import asyncio

load_dotenv()

# =========================================================
# 1. KONFIGURASI LOKASI KAMPUS (Multi Geofence)
# =========================================================

CAMPUS_LOCATIONS = [
    {
        "name": os.getenv("LOCATION_A_NAME", "Gedung A"),
        "latitude": float(os.getenv("LOCATION_A_LAT", -6.123456)),
        "longitude": float(os.getenv("LOCATION_A_LON", 106.123456)),
        "radius": float(os.getenv("LOCATION_A_RADIUS", 35))  # meter
    },
    {
        "name": os.getenv("LOCATION_B_NAME", "Gedung B"),
        "latitude": float(os.getenv("LOCATION_B_LAT", -6.123999)),
        "longitude": float(os.getenv("LOCATION_B_LON", 106.124500)),
        "radius": float(os.getenv("LOCATION_B_RADIUS", 40))
    },
    # Tambahkan lebih banyak lokasi sesuai kebutuhan
]

# =========================================================
# 2. CACHE & HISTORY (In-Memory)
# =========================================================

_location_history = defaultdict(lambda: {
    "lat": None,
    "lon": None,
    "timestamp": None,
    "accuracy": None
})
_ip_cache = {}

# =========================================================
# 3. FUNGSI UTILITY DASAR
# =========================================================

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak dalam meter menggunakan formula Haversine."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_to_nearest(lat: float, lon: float) -> Tuple[Optional[Dict], float]:
    """Cari lokasi kampus terdekat dan jaraknya dalam meter."""
    best = None
    best_dist = float('inf')
    for loc in CAMPUS_LOCATIONS:
        d = haversine_m(lat, lon, loc["latitude"], loc["longitude"])
        if d < best_dist:
            best_dist = d
            best = loc
    return best, best_dist


def calculate_median(values: List[float]) -> float:
    """Hitung median dari list angka."""
    return statistics.median(values) if values else 0.0


def calculate_std(values: List[float]) -> float:
    """Hitung standar deviasi populasi."""
    return statistics.pstdev(values) if len(values) > 1 else 0.0


# =========================================================
# 4. FUNGSI VALIDASI GPS SAMPLING (DIREVISI)
# =========================================================

def validate_gps_samples(samples: List[Dict]) -> Tuple[bool, Dict, Tuple[float, float]]:
    """
    Validasi multi-sampling GPS dengan algoritma yang lebih cerdas.
    
    Process:
        1. Hitung median koordinat (lebih tahan outlier)
        2. Buang sample dengan deviasi > 30 meter dari median
        3. Hitung mean dari sample yang tersisa
        4. Hitung standar deviasi lat/lon
        5. Hitung consistency_score
        6. Deteksi GPS stability (movement < 0.5m selama 3 detik)
    
    Returns:
        valid: bool
        details: dict berisi semua metrics
        (avg_lat, avg_lon): koordinat rata-rata setelah filtering
    """
    if not samples or len(samples) < 3:
        return False, {"error": "Minimal 3 sampel GPS diperlukan"}, (None, None)

    # Ekstrak koordinat
    lats = [s["lat"] for s in samples]
    lons = [s["lon"] for s in samples]
    timestamps = [s.get("timestamp", datetime.now().timestamp()) for s in samples]

    # 1. Median sebagai referensi awal
    median_lat = calculate_median(lats)
    median_lon = calculate_median(lons)

    # 2. Hitung jarak setiap sample ke median
    distances_to_median = [
        haversine_m(s["lat"], s["lon"], median_lat, median_lon)
        for s in samples
    ]

    # 3. Buang outlier (> 30 meter dari median)
    outlier_threshold = 30.0  # meter
    filtered_indices = [i for i, d in enumerate(distances_to_median) if d <= outlier_threshold]

    if len(filtered_indices) < 3:
        return False, {"error": "Terlalu banyak outlier GPS (>30m dari median)"}, (None, None)

    filtered_samples = [samples[i] for i in filtered_indices]
    filtered_lats = [s["lat"] for s in filtered_samples]
    filtered_lons = [s["lon"] for s in filtered_samples]

    # 4. Hitung mean dari filtered data
    avg_lat = statistics.mean(filtered_lats)
    avg_lon = statistics.mean(filtered_lons)

    # 5. Standar deviasi
    std_lat = calculate_std(filtered_lats)
    std_lon = calculate_std(filtered_lons)

    # 6. Jarak setiap sample ke rata-rata
    distances_to_mean = [
        haversine_m(s["lat"], s["lon"], avg_lat, avg_lon)
        for s in filtered_samples
    ]
    max_deviation = max(distances_to_mean) if distances_to_mean else 0
    avg_accuracy = statistics.mean([s.get("accuracy", 50) for s in filtered_samples])

    # 7. Consistency Score
    # Semakin kecil std dan max_deviation, semakin tinggi score
    # Normalisasi: std < 2m → 100, std 2-10m → 80, std > 20m → 40
    if max_deviation < 2 and std_lat < 2 and std_lon < 2:
        consistency_score = 100
    elif max_deviation < 5 and std_lat < 5 and std_lon < 5:
        consistency_score = 80
    elif max_deviation < 15 and std_lat < 15 and std_lon < 15:
        consistency_score = 50
    else:
        consistency_score = 20

    # 8. GPS Stability Detection (movement antar sample)
    # Hitung total perpindahan selama sampling
    total_movement = 0
    for i in range(1, len(filtered_samples)):
        d = haversine_m(
            filtered_samples[i-1]["lat"], filtered_samples[i-1]["lon"],
            filtered_samples[i]["lat"], filtered_samples[i]["lon"]
        )
        total_movement += d

    # Jika total movement < 0.5 meter dalam 3 detik → terlalu stabil
    time_diff = (timestamps[-1] - timestamps[0]) / 1000 if len(timestamps) > 1 else 0  # detik
    gps_stable = total_movement < 0.5 and time_diff > 2.5  # stabil selama >2.5 detik

    # 9. Build details
    details = {
        "raw_samples": len(samples),
        "filtered_samples": len(filtered_samples),
        "removed_outliers": len(samples) - len(filtered_samples),
        "median_coordinate": {"lat": round(median_lat, 6), "lon": round(median_lon, 6)},
        "average_coordinate": {"lat": round(avg_lat, 6), "lon": round(avg_lon, 6)},
        "std_lat": round(std_lat, 3),
        "std_lon": round(std_lon, 3),
        "max_deviation": round(max_deviation, 1),
        "avg_accuracy": round(avg_accuracy, 1),
        "consistency_score": consistency_score,
        "gps_stable": gps_stable,
        "total_movement": round(total_movement, 2),
        "time_diff_seconds": round(time_diff, 1),
    }

    # 10. Hitung mock_score tambahan dari GPS sampling
    mock_score = 0
    warnings = []

    # Jika consistency_score rendah → tambah skor
    if consistency_score < 30:
        mock_score += 15
        warnings.append(f"Konsistensi GPS rendah (skor {consistency_score})")
    elif consistency_score < 50:
        mock_score += 5
        warnings.append(f"Konsistensi GPS sedang (skor {consistency_score})")

    # Jika GPS terlalu stabil
    if gps_stable:
        mock_score += 10
        warnings.append("GPS terlalu stabil (movement <0.5m dalam 3 detik)")

    # Jika avg_accuracy > 100m
    if avg_accuracy > 100:
        mock_score += 15
        warnings.append(f"Akurasi rata-rata {avg_accuracy:.1f}m (>100m)")
    elif avg_accuracy > 50:
        mock_score += 5
        warnings.append(f"Akurasi rata-rata {avg_accuracy:.1f}m (>50m)")

    # Jika max_deviation > 30m
    if max_deviation > 30:
        mock_score += 10
        warnings.append(f"Deviasi maksimum {max_deviation:.1f}m (>30m)")

    details["mock_score"] = mock_score
    details["warnings"] = warnings

    return True, details, (avg_lat, avg_lon)


# =========================================================
# 5. FUNGSI VALIDASI LOKASI UTAMA (DIREVISI)
# =========================================================

def validate_location(
    lat: float,
    lon: float,
    user_id: Optional[str] = None,
    accuracy: Optional[float] = None,
    ip: Optional[str] = None,
    strict: bool = False,
    gps_samples: Optional[List[Dict]] = None,
) -> Tuple[bool, str, Dict]:
    """
    Validasi lokasi dengan multi-geofence + multi-sampling GPS + mock detection.

    Args:
        lat, lon: koordinat GPS
        user_id: ID user untuk history kecepatan
        accuracy: akurasi GPS (meter)
        ip: alamat IP untuk IP geolocation
        strict: jika True, tolak jika mock_score > 60
        gps_samples: list dict berisi lat, lon, accuracy, timestamp

    Returns:
        (valid, message, details)
    """
    if lat is None or lon is None:
        return False, "Lokasi tidak ditemukan.", {}

    # --- 1. Proses GPS Sampling jika ada ---
    gps_details = {}
    if gps_samples and len(gps_samples) >= 3:
        valid, details, (avg_lat, avg_lon) = validate_gps_samples(gps_samples)
        gps_details = details
        if not valid:
            return False, f"GPS sampling gagal: {details.get('error')}", {"gps": details}
        # Gunakan koordinat rata-rata yang sudah difilter
        lat, lon = avg_lat, avg_lon
        mock_score_from_sampling = details.get("mock_score", 0)
    else:
        mock_score_from_sampling = 0

    # --- 2. Geofence ---
    nearest, dist = distance_to_nearest(lat, lon)
    if nearest is None:
        return False, "Tidak ada lokasi kampus.", {}

    is_valid_geofence = dist <= nearest["radius"]

    # --- 3. Mock Detection ---
    # Inisialisasi skor dan warning
    mock_score = 0
    warnings = []

    # 3a. Accuracy (bobot 20%)
    if accuracy is not None:
        acc_score, acc_warning = _check_accuracy(accuracy)
        mock_score += acc_score
        warnings.extend(acc_warning)

    # 3b. Speed (bobot 35%)
    if user_id:
        speed_score, speed_warning = _check_speed(user_id, lat, lon)
        mock_score += speed_score
        warnings.extend(speed_warning)

        # Update history lokasi
        _location_history[user_id] = {
            "lat": lat,
            "lon": lon,
            "timestamp": datetime.now(),
            "accuracy": accuracy
        }

    # 3c. IP vs GPS (bobot 15%)
    if ip:
        ip_score, ip_warning = _check_ip_vs_gps(ip, lat, lon)
        mock_score += ip_score
        warnings.extend(ip_warning)

    # 3d. Tambahkan dari GPS Sampling (bobot 30%)
    mock_score += mock_score_from_sampling
    warnings.extend(gps_details.get("warnings", []))

    # 3e. Normalisasi mock_score ke 0-100
    # Max skor teoritis: accuracy 25 + speed 40 + IP 15 + sampling 25 = 105 → clamp ke 100
    mock_score = min(100, max(0, mock_score))

    # --- 4. Keputusan ---
    # Bobot: Accuracy 20%, Speed 35%, IP 15%, GPS Sampling 30%
    # mock_score sudah mencakup semua
    if not is_valid_geofence:
        decision = "rejected"
        msg = f"Di luar area kampus. Terdekat: {nearest['name']} ({dist:.1f}m)"
    elif strict and mock_score > 60:
        decision = "rejected"
        msg = f"Indikasi fake GPS kuat (skor {mock_score})."
    elif mock_score > 60:
        decision = "warning"
        msg = f"Indikasi fake GPS (skor {mock_score}), harap verifikasi."
    elif mock_score > 30:
        decision = "warning"
        msg = f"Lokasi valid dengan catatan (skor {mock_score})."
    else:
        decision = "valid"
        msg = f"Berada di {nearest['name']} ({dist:.1f}m)"

    # --- 5. Build details ---
    details = {
        "location": nearest["name"],
        "distance": round(dist, 1),
        "radius": nearest["radius"] if is_valid_geofence else None,
        "mock_score": mock_score,
        "decision": decision,
        "warnings": warnings,
        "gps_sampling": gps_details,
        "accuracy_used": accuracy,
        "ip_used": ip,
    }

    # Jika ada warning, tambahkan ke message
    if decision == "warning":
        msg += f" (skor {mock_score})"

    return decision != "rejected", msg, details


# =========================================================
# 6. HELPER FUNCTIONS UNTUK MOCK DETECTION (DIREVISI)
# =========================================================

def _check_accuracy(accuracy: float) -> Tuple[int, List[str]]:
    """
    Cek akurasi GPS dengan threshold yang lebih realistis.
    Bobot: 20%
    """
    if accuracy is None:
        return 0, []
    if accuracy < 2:
        return 10, ["Akurasi terlalu sempurna (<2m)"]
    elif accuracy < 30:
        return 0, []  # normal
    elif accuracy < 80:
        return 0, ["Akurasi sedang (30-80m)"]  # hanya warning, tidak tambah skor
    elif accuracy < 150:
        return 15, [f"Akurasi rendah ({accuracy:.1f}m)"]
    else:
        return 25, [f"Akurasi sangat rendah ({accuracy:.1f}m)"]


def _check_speed(user_id: str, lat: float, lon: float) -> Tuple[int, List[str]]:
    """
    Cek kecepatan berbasis history dengan validasi waktu & jarak.
    Bobot: 35%
    """
    last = _location_history.get(user_id)
    if not last or last["lat"] is None or last["timestamp"] is None:
        return 0, []

    now = datetime.now()
    delta_seconds = (now - last["timestamp"]).total_seconds()

    # Jika history > 5 menit, abaikan
    if delta_seconds > 300:
        return 0, []

    dist = haversine_m(last["lat"], last["lon"], lat, lon)

    # Jika jarak < 10m, dianggap normal
    if dist < 10:
        return 0, []

    # Jika selisih waktu < 5 detik dan jarak > 500m
    if delta_seconds < 5 and dist > 500:
        return 30, [f"Pergerakan terlalu cepat ({dist:.0f}m dalam {delta_seconds:.1f}s)"]

    # Jika jarak > 2km dalam <10 detik
    if delta_seconds < 10 and dist > 2000:
        return 40, [f"Pergerakan ekstrem ({dist:.0f}m dalam {delta_seconds:.1f}s)"]

    # Kecepatan umum (km/jam)
    speed_kmh = (dist / 1000) / (delta_seconds / 3600) if delta_seconds > 0 else 0
    if speed_kmh > 200:
        return 30, [f"Kecepatan tidak realistis ({speed_kmh:.0f} km/jam)"]
    elif speed_kmh > 100:
        return 15, [f"Kecepatan tinggi ({speed_kmh:.0f} km/jam)"]

    return 0, []


def _check_ip_vs_gps(ip: str, lat: float, lon: float) -> Tuple[int, List[str]]:
    """
    Bandingkan GPS dengan IP geolocation (hanya sebagai warning).
    Bobot: 15%
    """
    if not ip or ip in ["127.0.0.1", "::1", "localhost"]:
        return 0, []

    if ip in _ip_cache:
        ip_loc = _ip_cache[ip]
    else:
        try:
            r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
            if r.status_code == 200:
                data = r.json()
                if data.get("latitude") and data.get("longitude"):
                    ip_loc = {"lat": data["latitude"], "lon": data["longitude"]}
                    _ip_cache[ip] = ip_loc
                else:
                    return 0, []
            else:
                return 0, []
        except Exception:
            return 0, []

    if ip_loc:
        d = haversine_m(lat, lon, ip_loc["lat"], ip_loc["lon"])
        if d > 100000:  # >100 km
            return 15, [f"GPS vs IP: {d/1000:.1f} km (jauh)"]
        elif d > 50000:  # 50-100 km
            return 10, [f"GPS vs IP: {d/1000:.1f} km"]
        elif d > 20000:  # 20-50 km
            return 5, [f"GPS vs IP: {d/1000:.1f} km (warning)"]
    return 0, []


# =========================================================
# 7. LOGGING (Tetap)
# =========================================================

async def log_location_validation(
    user_id: str,
    lat: float,
    lon: float,
    is_valid: bool,
    details: Dict
):
    """Simpan log validasi ke database untuk audit."""
    try:
        from config.database import db
        await asyncio.to_thread(db.location_logs.insert_one, {
            "user_id": user_id,
            "latitude": lat,
            "longitude": lon,
            "validation_result": "valid" if is_valid else "invalid",
            "details": details,
            "timestamp": datetime.now()
        })
    except Exception:
        pass  # ignore jika database tidak tersedia


# =========================================================
# 8. DEBUG ENDPOINT (Tetap)
# =========================================================

def get_debug_info():
    """Untuk endpoint debug (opsional)."""
    return {
        "location_history": {
            k: {
                "lat": v["lat"],
                "lon": v["lon"],
                "timestamp": str(v["timestamp"])
            }
            for k, v in _location_history.items() if v["lat"] is not None
        },
        "ip_cache": list(_ip_cache.keys())
    }