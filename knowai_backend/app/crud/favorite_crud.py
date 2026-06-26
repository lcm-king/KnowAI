from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Course, Favorite, User


async def toggle_favorite(db: AsyncSession, user: User, course_id: int) -> bool:
    """Toggle favorite. Returns True if favorited, False if removed."""
    existing = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.course_id == course_id)
    )
    fav = existing.scalar_one_or_none()
    if fav is not None:
        await db.delete(fav)
        await db.commit()
        return False
    new_fav = Favorite(user_id=user.id, course_id=course_id)
    db.add(new_fav)
    await db.commit()
    await db.refresh(new_fav)
    return True


async def list_user_favorites(
    db: AsyncSession,
    user: User,
    page: int,
    page_size: int,
) -> tuple[int, list[Course]]:
    base_filter = Favorite.user_id == user.id
    count_stmt = select(func.count()).select_from(
        select(Course).join(Favorite).where(base_filter).subquery()
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(Course)
        .join(Favorite)
        .where(base_filter)
        .options(selectinload(Course.teacher), selectinload(Course.skus))
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return total, list(result.scalars().all())


async def is_favorited(db: AsyncSession, user: User, course_id: int) -> bool:
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.course_id == course_id)
    )
    return result.scalar_one_or_none() is not None
