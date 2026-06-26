from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_current_user_optional
from app.crud import course_crud
from app.database import get_db
from app.models import Chapter, Course, CourseSKU, CourseStatus, Lesson, SeckillActivity, SeckillStatus, SKUStatus, User, UserCourse
from app.schemas import (
    ChapterRead,
    CourseDetailListResponse,
    CourseDetailRead,
    CourseSKURead,
    LessonRead,
    MyLearningCourseItem,
    MyLearningResponse,
)

router = APIRouter()


async def attach_seckill(db: AsyncSession, course: Course) -> CourseDetailRead:
    item = CourseDetailRead.model_validate(course)
    result = await db.execute(
        select(SeckillActivity)
        .join(CourseSKU, CourseSKU.id == SeckillActivity.sku_id)
        .where(
            CourseSKU.course_id == course.id,
            SeckillActivity.status == SeckillStatus.active,
            SeckillActivity.start_time <= datetime.now(),
            SeckillActivity.end_time > datetime.now(),
        )
        .order_by(SeckillActivity.seckill_price.asc())
        .limit(1)
    )
    activity = result.scalar_one_or_none()
    if activity is not None:
        item.seckill_activity_id = activity.id
        item.seckill_price = activity.seckill_price
        item.seckill_end_time = activity.end_time
    return item


@router.get("", response_model=CourseDetailListResponse)
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    keyword: str | None = None,
    price_sort: Literal["asc", "desc"] | None = None,
) -> CourseDetailListResponse:
    total, courses = await course_crud.list_public_courses(db, page, page_size, category, keyword, price_sort)
    return CourseDetailListResponse(total=total, items=[await attach_seckill(db, course) for course in courses])


@router.get("/my-learning", response_model=MyLearningResponse)
async def list_my_learning(
    db: Annotated[AsyncSession, Depends(get_db)],
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
    items: list[MyLearningCourseItem] = []

    # Determine which courses have paid SKUs (to distinguish trial vs fully-free)
    all_course_ids = {uc.course_id for uc in result.scalars().all() if uc.course_id}
    # Re-fetch the result since we consumed it above
    result = await db.execute(
        select(UserCourse)
        .where(UserCourse.user_id == current_user.id)
        .options(
            selectinload(UserCourse.course),
            selectinload(UserCourse.sku),
        )
        .order_by(UserCourse.created_at.desc())
    )
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

    for uc in result.scalars().all():
        course = uc.course
        if course is None:
            continue
        progress = max(0, min(100, int((course.learn_count % 100))))
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
                progress=progress,
                is_trial=is_trial,
            )
        )
    return MyLearningResponse(total=len(items), items=items)


@router.get("/{course_id}", response_model=CourseDetailRead)
async def get_course_detail(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CourseDetailRead:
    course = await course_crud.get_public_course_detail(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    item = await attach_seckill(db, course)
    # Check if current user has purchased this course
    if current_user is not None:
        uc_result = await db.execute(
            select(UserCourse).where(
                UserCourse.user_id == current_user.id,
                UserCourse.course_id == course_id,
            )
        )
        item.is_purchased = uc_result.scalar_one_or_none() is not None
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
    has_paid = False
    if current_user is not None:
        uc_result = await db.execute(
            select(UserCourse)
            .where(UserCourse.user_id == current_user.id, UserCourse.course_id == course_id)
            .options(selectinload(UserCourse.sku))
        )
        user_courses = list(uc_result.scalars().all())
        has_paid = any(uc.sku and uc.sku.price > 0 for uc in user_courses)

    # Count total lessons across all chapters
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
            if not has_paid:
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
