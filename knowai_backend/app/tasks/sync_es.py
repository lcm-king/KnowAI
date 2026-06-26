from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Course, CourseSKU, CourseStatus, SKUStatus
from app.utils.es import delete_course_document, get_es_client, index_course_document


def decimal_to_float(value: Decimal | None) -> float:
    return float(value or Decimal("0.00"))


async def build_course_document(course_id: int) -> dict | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.teacher), selectinload(Course.skus))
        )
        course = result.scalar_one_or_none()
        if course is None:
            return None

        on_skus = [sku for sku in course.skus if sku.status == SKUStatus.on]
        price_min = min((sku.price for sku in on_skus), default=Decimal("0.00"))
        return {
            "course_id": course.id,
            "title": course.title,
            "description": course.description or "",
            "cover": course.cover or "",
            "category": course.category or "",
            "teacher_name": course.teacher.name,
            "price_min": decimal_to_float(price_min),
            "sales": course.learn_count,
            "rating": course.rating,
            "status": course.status.value,
            "created_at": course.created_at.isoformat() if course.created_at else None,
        }


async def sync_course_to_es(course_id: int) -> None:
    document = await build_course_document(course_id)
    es = get_es_client()
    try:
        if document is None or document["status"] in {CourseStatus.draft.value, CourseStatus.closed.value}:
            await delete_course_document(es, course_id)
            print(f"Deleted course {course_id} from Elasticsearch")
            return
        await index_course_document(es, document)
        print(f"Synced course {course_id} to Elasticsearch")
    finally:
        await es.close()


async def delete_course_from_es(course_id: int) -> None:
    es = get_es_client()
    try:
        await delete_course_document(es, course_id)
        print(f"Deleted course {course_id} from Elasticsearch")
    finally:
        await es.close()
