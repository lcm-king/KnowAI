from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


async def create_note(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    lesson_id: int,
    course_id: int,
    content: str,
    timestamp: float = 0,
) -> dict:
    doc = {
        "user_id": user_id,
        "lesson_id": lesson_id,
        "course_id": course_id,
        "content": content,
        "timestamp": timestamp,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    result = await mongo.lesson_notes.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def update_note(mongo: AsyncIOMotorDatabase, note_id: str, user_id: int, content: str, timestamp: float = 0) -> dict | None:
    from bson import ObjectId
    result = await mongo.lesson_notes.find_one_and_update(
        {"_id": ObjectId(note_id), "user_id": user_id},
        {"$set": {"content": content, "timestamp": timestamp, "updated_at": datetime.now()}},
        return_document=ReturnDocument.AFTER,
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


async def delete_note(mongo: AsyncIOMotorDatabase, note_id: str, user_id: int) -> bool:
    from bson import ObjectId
    result = await mongo.lesson_notes.delete_one({"_id": ObjectId(note_id), "user_id": user_id})
    return result.deleted_count > 0


async def list_lesson_notes(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    lesson_id: int,
) -> list[dict]:
    cursor = mongo.lesson_notes.find(
        {"user_id": user_id, "lesson_id": lesson_id}
    ).sort("timestamp", 1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


async def list_course_notes(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
    lesson_id: int | None = None,
) -> list[dict]:
    query: dict = {"user_id": user_id, "course_id": course_id}
    if lesson_id is not None:
        query["lesson_id"] = lesson_id
    cursor = mongo.lesson_notes.find(query).sort("created_at", -1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items
