from datetime import datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Course, CourseSKU, Order, OrderItem, SKUStatus, UserCourse


async def grant_courses_for_order(db: AsyncSession, order: Order, redis: Redis | None = None) -> None:
    result = await db.execute(
        select(OrderItem)
        .where(OrderItem.order_id == order.id)
        .options(selectinload(OrderItem.sku).selectinload(CourseSKU.course))
    )
    items = list(result.scalars().all())
    for item in items:
        # Check if course has paid SKUs (trial vs fully-free)
        paid_sku = await db.execute(
            select(CourseSKU.id)
            .where(CourseSKU.course_id == item.sku.course_id, CourseSKU.price > 0, CourseSKU.status == SKUStatus.on)
            .limit(1)
        )
        has_paid_sku = paid_sku.first() is not None
        expire_date = None if (item.price > 0 or not has_paid_sku) else datetime.now() + timedelta(days=item.sku.validity_days)
        existing_result = await db.execute(
            select(UserCourse).where(
                UserCourse.user_id == order.user_id,
                UserCourse.course_id == item.sku.course_id,
                UserCourse.sku_id == item.sku_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is None:
            db.add(
                UserCourse(
                    user_id=order.user_id,
                    course_id=item.sku.course_id,
                    sku_id=item.sku_id,
                    expire_date=expire_date,
                )
            )
        elif existing.expire_date is None:
            pass  # already permanent, keep it
        elif expire_date is None:
            existing.expire_date = None  # upgrade to permanent
        elif existing.expire_date < expire_date:
            existing.expire_date = expire_date
        item.sku.course.learn_count += item.quantity

        # Track in Redis hot ZSet
        if redis is not None:
            await redis.zincrby("top:courses", 10, str(item.sku.course_id))
