import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models import Course
from app.tasks.sync_es import sync_course_to_es
from app.utils.es import ensure_courses_index, get_es_client


async def init_es() -> None:
    es = get_es_client()
    try:
        await ensure_courses_index(es)
    finally:
        await es.close()


async def sync_existing_courses() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Course.id))
        course_ids = list(result.scalars().all())

    for course_id in course_ids:
        await sync_course_to_es(course_id)


async def main() -> None:
    await init_es()
    await sync_existing_courses()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
