from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

LESSON_PROGRESS_COLLECTION = "lesson_progress"
COURSE_PROGRESS_COLLECTION = "course_progress"


async def upsert_lesson_progress(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
    lesson_id: int,
    position: float,
    duration: float | None = None,
) -> None:
    """更新某课时的观看进度(upsert)。"""
    now = datetime.utcnow()
    update: dict[str, Any] = {
        "user_id": user_id,
        "course_id": course_id,
        "lesson_id": lesson_id,
        "position": position,
        "updated_at": now,
    }
    if duration is not None:
        update["duration"] = duration
    await mongo[LESSON_PROGRESS_COLLECTION].update_one(
        {"user_id": user_id, "lesson_id": lesson_id},
        {"$set": update, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def get_lesson_progress(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    lesson_id: int,
) -> dict[str, Any] | None:
    doc = await mongo[LESSON_PROGRESS_COLLECTION].find_one(
        {"user_id": user_id, "lesson_id": lesson_id}
    )
    if doc is None:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


async def list_course_progress(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
) -> list[dict[str, Any]]:
    cursor = mongo[LESSON_PROGRESS_COLLECTION].find(
        {"user_id": user_id, "course_id": course_id}
    )
    items: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items


async def get_course_progress_summary(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
    total_lessons: int,
) -> dict[str, Any]:
    """汇总某课程的学习进度:已学课时数、进度百分比、最后观看课时。"""
    rows = await list_course_progress(mongo, user_id, course_id)
    if not rows:
        return {"learned_lessons": 0, "progress": 0, "last_lesson_id": None, "last_position": 0.0}
    learned = len(rows)
    progress = int(learned / total_lessons * 100) if total_lessons > 0 else 0
    last = max(rows, key=lambda r: r.get("updated_at") or datetime.min)
    return {
        "learned_lessons": learned,
        "progress": min(progress, 100),
        "last_lesson_id": last.get("lesson_id"),
        "last_position": last.get("position", 0.0),
    }


async def upsert_course_last_view(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
    lesson_id: int,
) -> None:
    """记录用户在某课程最后观看的课时(用于"继续学习")。"""
    now = datetime.utcnow()
    await mongo[COURSE_PROGRESS_COLLECTION].update_one(
        {"user_id": user_id, "course_id": course_id},
        {"$set": {"last_lesson_id": lesson_id, "updated_at": now},
         "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def get_course_last_view(
    mongo: AsyncIOMotorDatabase,
    user_id: int,
    course_id: int,
) -> int | None:
    doc = await mongo[COURSE_PROGRESS_COLLECTION].find_one(
        {"user_id": user_id, "course_id": course_id}
    )
    if doc is None:
        return None
    return doc.get("last_lesson_id")
