import os
from dotenv import load_dotenv
from utils.haversine import haversine

load_dotenv()

ALLOWED_LAT = float(os.getenv("ALLOWED_LAT"))
ALLOWED_LON = float(os.getenv("ALLOWED_LON"))
MAX_RADIUS_KM = float(os.getenv("MAX_RADIUS_KM"))

def validate_location(lat, lon):
    if lat is None or lon is None:
        return False, "Lokasi tidak dikirim. Pastikan GPS aktif."
    distance = haversine(lat, lon, ALLOWED_LAT, ALLOWED_LON)
    if distance > MAX_RADIUS_KM:
        return False, f"Anda berada di luar radius absensi ({distance:.2f} km dari kampus)"
    return True, f"Lokasi valid, jarak: {distance:.2f} km"