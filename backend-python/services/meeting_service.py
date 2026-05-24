from config.database import db
from bson import ObjectId
import asyncio

async def get_active_meeting(course_id):
    # course_id adalah ObjectId
    meeting = await asyncio.to_thread(
        db['meetings'].find_one,
        {"course_id": course_id, "status": "active"}
    )
    return meeting