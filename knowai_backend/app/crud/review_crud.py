from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Course, CourseReview
from app.schemas import ReviewCreate, ReviewUpdate


async def create_review(db: AsyncSession, course_id: int, user_id: int, review_in: ReviewCreate) -> CourseReview:
    review = CourseReview(course_id=course_id, user_id=user_id, **review_in.model_dump())
    db.add(review)
    await db.flush()
    await recalc_course_rating(db, course_id)
    await db.refresh(review)
    return review


async def get_review(db: AsyncSession, review_id: int) -> CourseReview | None:
    return await db.get(CourseReview, review_id)


async def get_user_course_review(db: AsyncSession, course_id: int, user_id: int) -> CourseReview | None:
    result = await db.execute(
        select(CourseReview).where(
            CourseReview.course_id == course_id,
            CourseReview.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_review(db: AsyncSession, review: CourseReview, review_in: ReviewUpdate) -> CourseReview:
    changed = False
    for key, value in review_in.model_dump(exclude_unset=True).items():
        setattr(review, key, value)
        changed = True
    if changed:
        await db.flush()
        await recalc_course_rating(db, review.course_id)
        await db.refresh(review)
    return review


async def delete_review(db: AsyncSession, review: CourseReview) -> None:
    course_id = review.course_id
    await db.delete(review)
    await db.flush()
    await recalc_course_rating(db, course_id)


async def list_course_reviews(
    db: AsyncSession,
    course_id: int,
    page: int,
    page_size: int,
) -> tuple[int, list[CourseReview]]:
    stmt = (
        select(CourseReview)
        .where(CourseReview.course_id == course_id)
        .options(selectinload(CourseReview.user))
        .order_by(CourseReview.created_at.desc())
    )
    total_result = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    total = total_result.scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return int(total or 0), list(result.scalars().all())


async def list_all_reviews(
    db: AsyncSession,
    page: int,
    page_size: int,
    course_id: int | None = None,
) -> tuple[int, list[CourseReview]]:
    stmt = (
        select(CourseReview)
        .options(selectinload(CourseReview.user), selectinload(CourseReview.course))
        .order_by(CourseReview.created_at.desc())
    )
    if course_id is not None:
        stmt = stmt.where(CourseReview.course_id == course_id)
    total_result = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    total = total_result.scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return int(total or 0), list(result.scalars().all())


async def recalc_course_rating(db: AsyncSession, course_id: int) -> float:
    """Recalculate average rating from all reviews and update Course.rating."""
    result = await db.execute(
        select(func.coalesce(func.avg(CourseReview.rating), 0))
        .where(CourseReview.course_id == course_id)
    )
    avg = float(result.scalar_one() or 0)
    course = await db.get(Course, course_id)
    if course is not None:
        course.rating = round(avg, 1)
        await db.flush()
    return round(avg, 1)
