from datetime import datetime

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Course, CourseReview, CourseSKU, CourseStatus, Favorite, SeckillActivity, SeckillStatus, SKUStatus, Teacher, UserCourse
from app.schemas import CourseCreate, CourseSKUCreate, CourseSKUUpdate, CourseUpdate


async def get_teacher_by_user_id(db: AsyncSession, user_id: int) -> Teacher | None:
    result = await db.execute(select(Teacher).where(Teacher.user_id == user_id))
    return result.scalar_one_or_none()


async def create_course(db: AsyncSession, teacher_id: int, course_in: CourseCreate) -> Course:
    course = Course(teacher_id=teacher_id, **course_in.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def get_teacher_course(db: AsyncSession, teacher_id: int, course_id: int) -> Course | None:
    result = await db.execute(select(Course).where(Course.id == course_id, Course.teacher_id == teacher_id))
    return result.scalar_one_or_none()


async def update_course(db: AsyncSession, course: Course, course_in: CourseUpdate) -> Course:
    for key, value in course_in.model_dump(exclude_unset=True).items():
        setattr(course, key, value)
    await db.commit()
    await db.refresh(course)
    return course


async def submit_course(db: AsyncSession, course: Course) -> Course:
    course.status = CourseStatus.pending
    await db.commit()
    await db.refresh(course)
    return course


async def close_course(db: AsyncSession, course: Course) -> Course:
    course.status = CourseStatus.closed
    # 下架与删除同效:清除购买记录、收藏、评价
    await db.execute(delete(UserCourse).where(UserCourse.course_id == course.id))
    await db.execute(delete(Favorite).where(Favorite.course_id == course.id))
    await db.execute(delete(CourseReview).where(CourseReview.course_id == course.id))
    await db.commit()
    await db.refresh(course)
    return course


async def create_course_sku(db: AsyncSession, course_id: int, sku_in: CourseSKUCreate) -> CourseSKU:
    sku = CourseSKU(course_id=course_id, **sku_in.model_dump())
    db.add(sku)
    await db.commit()
    await db.refresh(sku)
    return sku


async def get_teacher_sku(db: AsyncSession, teacher_id: int, sku_id: int) -> CourseSKU | None:
    result = await db.execute(
        select(CourseSKU)
        .join(Course, Course.id == CourseSKU.course_id)
        .where(CourseSKU.id == sku_id, Course.teacher_id == teacher_id)
    )
    return result.scalar_one_or_none()


async def update_course_sku(db: AsyncSession, sku: CourseSKU, sku_in: CourseSKUUpdate) -> CourseSKU:
    for key, value in sku_in.model_dump(exclude_unset=True).items():
        setattr(sku, key, value)
    await db.commit()
    await db.refresh(sku)
    return sku


async def delete_course_sku(db: AsyncSession, sku: CourseSKU) -> CourseSKU:
    sku.status = SKUStatus.off
    await db.commit()
    await db.refresh(sku)
    return sku


async def list_teacher_courses(
    db: AsyncSession,
    teacher_id: int,
    page: int,
    page_size: int,
    status: CourseStatus | None = None,
) -> tuple[int, list[Course]]:
    stmt = (
        select(Course)
        .where(Course.teacher_id == teacher_id)
        .options(selectinload(Course.skus))
        .order_by(Course.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(Course.status == status)
    else:
        stmt = stmt.where(Course.status != CourseStatus.closed)
    return await paginate_courses(db, stmt, page, page_size)


async def list_public_courses(
    db: AsyncSession,
    page: int,
    page_size: int,
    category: str | None = None,
    keyword: str | None = None,
    price_sort: str | None = None,
) -> tuple[int, list[Course]]:
    stmt = (
        select(Course)
        .where(Course.status == CourseStatus.published)
        .options(selectinload(Course.teacher), selectinload(Course.skus))
    )
    if category:
        stmt = stmt.where(Course.category == category)
    if keyword:
        stmt = stmt.where(Course.title.like(f"%{keyword}%"))
    if price_sort in {"asc", "desc"}:
        min_price = select(func.min(CourseSKU.price)).where(
            CourseSKU.course_id == Course.id,
            CourseSKU.status == SKUStatus.on,
        ).scalar_subquery()
        stmt = stmt.order_by(min_price.asc() if price_sort == "asc" else min_price.desc())
    else:
        stmt = stmt.order_by(Course.created_at.desc())
    return await paginate_courses(db, stmt, page, page_size)


async def list_seckill_courses(db: AsyncSession, limit: int = 10) -> list[Course]:
    """List published courses that have active seckill activities."""
    now = datetime.now()
    result = await db.execute(
        select(Course)
        .join(CourseSKU, CourseSKU.course_id == Course.id)
        .join(SeckillActivity, SeckillActivity.sku_id == CourseSKU.id)
        .where(
            Course.status == CourseStatus.published,
            SeckillActivity.status == SeckillStatus.active,
            SeckillActivity.start_time <= now,
            SeckillActivity.end_time > now,
        )
        .options(selectinload(Course.teacher), selectinload(Course.skus))
        .order_by(SeckillActivity.end_time.asc())
        .limit(limit)
    )
    # Deduplicate by course id
    seen: set[int] = set()
    courses: list[Course] = []
    for course in result.scalars().all():
        if course.id not in seen:
            seen.add(course.id)
            courses.append(course)
    return courses


async def get_public_course_detail(db: AsyncSession, course_id: int) -> Course | None:
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.status == CourseStatus.published)
        .options(selectinload(Course.teacher), selectinload(Course.skus))
    )
    return result.scalar_one_or_none()


async def list_course_skus(db: AsyncSession, course_id: int) -> list[CourseSKU]:
    result = await db.execute(
        select(CourseSKU).where(CourseSKU.course_id == course_id, CourseSKU.status == SKUStatus.on)
    )
    return list(result.scalars().all())


async def paginate_courses(db: AsyncSession, stmt: Select[tuple[Course]], page: int, page_size: int) -> tuple[int, list[Course]]:
    total_result = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    total = total_result.scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return total, list(result.scalars().all())


# ── Admin helpers ──

async def get_course_by_id(db: AsyncSession, course_id: int) -> Course | None:
    """Get any course by ID (no teacher filter)."""
    return await db.get(Course, course_id)


async def list_all_courses(
    db: AsyncSession,
    page: int,
    page_size: int,
    status: CourseStatus | None = None,
    keyword: str | None = None,
) -> tuple[int, list[Course]]:
    """List all courses (admin view, no teacher filter)."""
    stmt = select(Course).options(selectinload(Course.teacher)).order_by(Course.created_at.desc())
    if status is not None:
        stmt = stmt.where(Course.status == status)
    else:
        stmt = stmt.where(Course.status != CourseStatus.closed)
    if keyword:
        stmt = stmt.where(Course.title.like(f"%{keyword}%"))
    return await paginate_courses(db, stmt, page, page_size)


async def delete_course_soft(db: AsyncSession, course: Course) -> Course:
    """Soft-delete a course by setting status to closed, and clear purchase records."""
    course.status = CourseStatus.closed
    # 同步清除购买记录、收藏、评价,避免购买者仍看到已下架课程
    await db.execute(delete(UserCourse).where(UserCourse.course_id == course.id))
    await db.execute(delete(Favorite).where(Favorite.course_id == course.id))
    await db.execute(delete(CourseReview).where(CourseReview.course_id == course.id))
    await db.commit()
    await db.refresh(course)
    return course
