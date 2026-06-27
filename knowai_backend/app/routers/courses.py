import json
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_current_user_optional
from app.crud import course_crud
from app.crud import progress_crud
from app.database import get_db, get_mongo, get_redis
from app.models import Chapter, Course, CourseSKU, CourseStatus, Lesson, SeckillActivity, SeckillStatus, SKUStatus, User, UserCourse
from app.schemas import (
    ChapterRead,
    CourseDetailListResponse,
    CourseDetailRead,
    CourseProgressSummary,
    CourseSKURead,
    LessonProgressUpdate,
    LessonRead,
    MyLearningCourseItem,
    MyLearningResponse,
)

router = APIRouter()

# Cache TTL for homepage course listing (seconds)
HOMEPAGE_CACHE_TTL = 60
HOMEPAGE_CACHE_KEY = "homepage:courses"


async def get_cached_homepage(redis: Redis) -> CourseDetailListResponse | None:
    """Try to fetch cached homepage course list from Redis."""
    data = await redis.get(HOMEPAGE_CACHE_KEY)
    if data is None:
        return None
    raw = json.loads(data)
    return CourseDetailListResponse(**raw)


async def set_cached_homepage(redis: Redis, response: CourseDetailListResponse) -> None:
    """Cache homepage course list in Redis."""
    raw = response.model_dump(mode="json")
    await redis.setex(HOMEPAGE_CACHE_KEY, HOMEPAGE_CACHE_TTL, json.dumps(raw, default=str))


async def invalidate_homepage_cache(redis: Redis) -> None:
    """Invalidate homepage cache when course data changes."""
    await redis.delete(HOMEPAGE_CACHE_KEY)


async def attach_seckill_bulk(db: AsyncSession, courses: list[Course]) -> list[CourseDetailRead]:
    """Attach seckill data to all courses in a single batch query."""
    if not courses:
        return []

    course_ids = [c.id for c in courses]
    now = datetime.now()
    result = await db.execute(
        select(SeckillActivity)
        .options(selectinload(SeckillActivity.sku))
        .join(CourseSKU, CourseSKU.id == SeckillActivity.sku_id)
        .where(
            CourseSKU.course_id.in_(course_ids),
            SeckillActivity.status == SeckillStatus.active,
            SeckillActivity.start_time <= now,
            SeckillActivity.end_time > now,
        )
        .order_by(SeckillActivity.seckill_price.asc())
    )
    # Map first (lowest price) activity per course
    seckill_map: dict[int, SeckillActivity] = {}
    for act in result.scalars().all():
        cid = act.sku.course_id
        if cid not in seckill_map:
            seckill_map[cid] = act

    items: list[CourseDetailRead] = []
    for course in courses:
        item = CourseDetailRead.model_validate(course)
        activity = seckill_map.get(course.id)
        if activity is not None:
            item.seckill_activity_id = activity.id
            item.seckill_price = activity.seckill_price
            item.seckill_end_time = activity.end_time
        items.append(item)
    return items


async def attach_seckill(db: AsyncSession, course: Course) -> CourseDetailRead:
    """Attach seckill for a single course (used by course detail page)."""
    items = await attach_seckill_bulk(db, [course])
    return items[0]


@router.get("/seckill", response_model=list[CourseDetailRead])
async def list_seckill_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> list[CourseDetailRead]:
    """List published courses with active seckill activities (max 10)."""
    cache_key = "homepage:seckill"
    cached = await redis.get(cache_key)
    if cached is not None:
        return [CourseDetailRead(**item) for item in json.loads(cached)]

    courses = await course_crud.list_seckill_courses(db, limit=10)
    items = await attach_seckill_bulk(db, courses)
    await redis.setex(cache_key, 30, json.dumps([i.model_dump(mode="json") for i in items], default=str))
    return items


@router.get("", response_model=CourseDetailListResponse)
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    keyword: str | None = None,
    price_sort: Literal["asc", "desc"] | None = None,
) -> CourseDetailListResponse:
    # Cache only the unfiltered home page listing
    if page == 1 and page_size <= 20 and not category and not keyword and not price_sort:
        cached = await get_cached_homepage(redis)
        if cached is not None:
            return cached

    total, courses = await course_crud.list_public_courses(db, page, page_size, category, keyword, price_sort)
    items = await attach_seckill_bulk(db, courses)
    response = CourseDetailListResponse(total=total, items=items)

    # Update cache for homepage listing
    if page == 1 and page_size <= 20 and not category and not keyword and not price_sort:
        await set_cached_homepage(redis, response)

    return response


@router.get("/my-learning", response_model=MyLearningResponse)
async def list_my_learning(
    db: Annotated[AsyncSession, Depends(get_db)],
    mongo: Annotated[Any, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MyLearningResponse:
    result = await db.execute(
        select(UserCourse)
        .where(UserCourse.user_id == current_user.id)
        .options(
            selectinload(UserCourse.course),
            selectinload(UserCourse.sku),
        )
        .order_by(UserCourse.created_at.desc())
    )
    user_courses = list(result.scalars().all())
    items: list[MyLearningCourseItem] = []

    all_course_ids = {uc.course_id for uc in user_courses if uc.course_id}
    courses_with_paid: set[int] = set()
    if all_course_ids:
        paid_rows = await db.execute(
            select(CourseSKU.course_id)
            .where(
                CourseSKU.course_id.in_(all_course_ids),
                CourseSKU.price > 0,
                CourseSKU.status == SKUStatus.on,
            )
            .distinct()
        )
        for row in paid_rows:
            courses_with_paid.add(row[0])

    # 统计每个课程的总课时数
    lesson_counts: dict[int, int] = {}
    if all_course_ids:
        lc_rows = await db.execute(
            select(Chapter.course_id, func.count(Lesson.id))
            .join(Lesson, Lesson.chapter_id == Chapter.id)
            .where(Chapter.course_id.in_(all_course_ids))
            .group_by(Chapter.course_id)
        )
        for cid, cnt in lc_rows.all():
            lesson_counts[int(cid)] = int(cnt)

    for uc in user_courses:
        course = uc.course
        if course is None:
            continue
        total_lessons = lesson_counts.get(course.id, 0)
        summary = await progress_crud.get_course_progress_summary(
            mongo, current_user.id, course.id, total_lessons
        )
        is_trial = uc.sku is not None and uc.sku.price == 0 and course.id in courses_with_paid
        items.append(
            MyLearningCourseItem(
                id=course.id,
                title=course.title,
                cover=course.cover,
                category=course.category,
                total_hours=course.total_hours,
                learn_count=course.learn_count,
                rating=course.rating,
                sku_id=uc.sku_id,
                sku_name=uc.sku.sku_name if uc.sku else None,
                expire_date=uc.expire_date,
                progress=summary["progress"],
                is_trial=is_trial,
            )
        )
    return MyLearningResponse(total=len(items), items=items)


@router.get("/{course_id}", response_model=CourseDetailRead)
async def get_course_detail(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CourseDetailRead:
    # Cache course detail for anonymous users
    cache_key = f"course:detail:{course_id}"
    if current_user is None:
        cached = await redis.get(cache_key)
        if cached is not None:
            return CourseDetailRead(**json.loads(cached))

    course = await course_crud.get_public_course_detail(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    item = await attach_seckill(db, course)
    # Track popularity in Redis ZSet
    await redis.zincrby("top:courses", 1, str(course_id))
    # Check if current user has purchased this course
    if current_user is not None:
        uc_result = await db.execute(
            select(UserCourse).where(
                UserCourse.user_id == current_user.id,
                UserCourse.course_id == course_id,
            )
        )
        item.is_purchased = uc_result.scalar_one_or_none() is not None
    else:
        # Cache anonymous response for 60s
        raw = item.model_dump(mode="json")
        await redis.setex(cache_key, 60, json.dumps(raw, default=str))
    return item


@router.get("/{course_id}/skus", response_model=list[CourseSKURead])
async def get_course_skus(course_id: int, db: Annotated[AsyncSession, Depends(get_db)]) -> list[CourseSKURead]:
    return await course_crud.list_course_skus(db, course_id)


@router.get("/{course_id}/chapters", response_model=list[ChapterRead])
async def get_course_chapters(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> list[ChapterRead]:
    """获取课程章节和课时列表，根据用户权限控制可访问的课时。"""
    result = await db.execute(
        select(Chapter)
        .where(Chapter.course_id == course_id)
        .options(selectinload(Chapter.lessons))
        .order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()

    # Determine if user has paid access (all lessons unlocked) or trial access (first 3 lessons only)
    # 查询该课程是否有付费 SKU:有则走试看逻辑,纯免费课程全部开放
    paid_sku_result = await db.execute(
        select(CourseSKU.id).where(
            CourseSKU.course_id == course_id,
            CourseSKU.price > 0,
            CourseSKU.status == SKUStatus.on,
        ).limit(1)
    )
    has_paid_sku = paid_sku_result.scalar_one_or_none() is not None

    has_paid = False
    if current_user is not None and has_paid_sku:
        uc_result = await db.execute(
            select(UserCourse)
            .where(UserCourse.user_id == current_user.id, UserCourse.course_id == course_id)
            .options(selectinload(UserCourse.sku))
        )
        user_courses = list(uc_result.scalars().all())
        has_paid = any(uc.sku and uc.sku.price > 0 for uc in user_courses)

    # 纯免费课程(无付费 SKU)所有课时开放;付费课程非购买者仅前 3 课时试看
    free_course = not has_paid_sku
    all_lessons = [lesson for chapter in chapters for lesson in chapter.lessons]
    all_lessons.sort(key=lambda l: l.sort_order)
    free_limit = 3  # first 3 lessons for free trial

    result_chapters: list[ChapterRead] = []
    for ch in chapters:
        lessons = list(ch.lessons)
        lessons.sort(key=lambda l: l.sort_order)
        chapter_read = ChapterRead(
            id=ch.id,
            title=ch.title,
            sort_order=ch.sort_order,
            lessons=[],
        )
        for lesson in lessons:
            is_locked = False
            if not free_course and not has_paid:
                # Find the global index of this lesson among all sorted lessons
                try:
                    idx = all_lessons.index(lesson)
                    is_locked = idx >= free_limit
                except ValueError:
                    is_locked = True
            chapter_read.lessons.append(
                LessonRead(
                    id=lesson.id,
                    title=lesson.title,
                    video_url=lesson.video_url if not is_locked else None,
                    duration=lesson.duration,
                    sort_order=lesson.sort_order,
                    is_locked=is_locked,
                )
            )
        result_chapters.append(chapter_read)
    return result_chapters


# ── Learning Progress ──


@router.post("/{course_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def update_lesson_progress(
    course_id: int,
    payload: LessonProgressUpdate,
    mongo: Annotated[Any, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await progress_crud.upsert_lesson_progress(
        mongo, current_user.id, course_id, payload.lesson_id,
        payload.position, payload.duration,
    )
    await progress_crud.upsert_course_last_view(
        mongo, current_user.id, course_id, payload.lesson_id,
    )


@router.get("/{course_id}/progress", response_model=CourseProgressSummary)
async def get_course_progress(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    mongo: Annotated[Any, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CourseProgressSummary:
    # 计算总课时数
    count_result = await db.execute(
        select(func.count(Lesson.id))
        .join(Chapter, Chapter.id == Lesson.chapter_id)
        .where(Chapter.course_id == course_id)
    )
    total_lessons = count_result.scalar_one() or 0
    summary = await progress_crud.get_course_progress_summary(
        mongo, current_user.id, course_id, total_lessons
    )
    return CourseProgressSummary(**summary)
