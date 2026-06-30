import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DATABASE_NAME", "faceDB")

client = MongoClient(MONGO_URI)
db = client[DB_NAME] 

faces_collection = db["faces"]
attendance_collection = db["attendances"]
# Di config/database.py
courses_collection = db["courses"]
enrollments_collection = db["enrollments"]
users_collection = db["users"]
manual_attendance_collection = db["manual_attendance"]

def test_connection():
    try:
        client.admin.command('ping')
        print("✅ MongoDB connected successfully")
        return True
    except Exception as e:
        print("❌ MongoDB connection error:", e)
        return False