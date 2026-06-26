import random
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.crud.user_course_crud import grant_courses_for_order
from app.models import Course, CourseSKU, CourseStatus, Order, OrderItem, OrderStatus, SKUStatus

LOCK_EXPIRE_SECONDS = 3


def generate_order_sn() -> str:
    return f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}{random.randint(1000, 9999)}"[:32]


def lock_key(sku_id: int) -> str:
    return f"lock:sku:{sku_id}"


async def acquire_sku_locks(redis: Redis, sku_ids: list[int]) -> list[str]:
    acquired: list[str] = []
    for sku_id in sorted(set(sku_ids)):
        key = lock_key(sku_id)
        locked = await redis.set(key, "1", nx=True, ex=LOCK_EXPIRE_SECONDS)
        if not locked:
            for acquired_key in acquired:
                await redis.delete(acquired_key)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="当前购买人数过多，请稍后重试")
        acquired.append(key)
    return acquired


async def release_sku_locks(redis: Redis, keys: list[str]) -> None:
    if keys:
        await redis.delete(*keys)


async def create_order(db: AsyncSession, redis: Redis, user_id: int, sku_ids: list[int], address_id: int | None) -> Order:
    if len(set(sku_ids)) != len(sku_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不允许重复的 SKU")

    lock_keys = await acquire_sku_locks(redis, sku_ids)
    try:
        result = await db.execute(
            select(CourseSKU)
            .where(CourseSKU.id.in_(sku_ids))
            .with_for_update()
            .options(selectinload(CourseSKU.course))
        )
        skus = list(result.scalars().all())
        sku_map = {sku.id: sku for sku in skus}
        if len(sku_map) != len(sku_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 SKU")

        for sku_id in sku_ids:
            sku = sku_map[sku_id]
            if sku.status != SKUStatus.on:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU {sku_id} 不可用")
            if sku.stock < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU {sku_id} 库存不足")
            if sku.course is None or sku.course.status != CourseStatus.published:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程不存在或已下架")
            sku.stock -= 1

        total_amount = sum((sku_map[sku_id].price for sku_id in sku_ids), Decimal("0.00"))
        order = Order(
            user_id=user_id,
            order_sn=generate_order_sn(),
            total_amount=total_amount,
            pay_amount=total_amount,
            expire_time=datetime.now() + timedelta(minutes=settings.order_expire_minutes),
            address=str(address_id) if address_id is not None else None,
        )
        db.add(order)
        await db.flush()

        for sku_id in sku_ids:
            db.add(OrderItem(order_id=order.id, sku_id=sku_id, quantity=1, price=sku_map[sku_id].price))

        await db.commit()
        await db.refresh(order)

        if total_amount == 0:
            # Free order: auto-grant without payment
            order.status = OrderStatus.paid
            order.pay_time = datetime.now()
            await grant_courses_for_order(db, order)
            await db.commit()
            await db.refresh(order)
        else:
            await redis.setex(f"order:delay:{order.order_sn}", settings.order_expire_minutes * 60, "1")

        return order
    except Exception:
        await db.rollback()
        raise
    finally:
        await release_sku_locks(redis, lock_keys)


async def get_user_order(db: AsyncSession, user_id: int, order_sn: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.order_sn == order_sn)
        .options(selectinload(Order.items).selectinload(OrderItem.sku).selectinload(CourseSKU.course))
    )
    return result.scalar_one_or_none()


async def list_user_orders(
    db: AsyncSession,
    user_id: int,
    page: int,
    page_size: int,
    status_filter: OrderStatus | None = None,
) -> tuple[int, list[Order]]:
    stmt = select(Order).where(Order.user_id == user_id)
    if status_filter is not None:
        stmt = stmt.where(Order.status == status_filter)
    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(Order.items).selectinload(OrderItem.sku).selectinload(CourseSKU.course))
    )
    return total, list(result.scalars().all())


async def cancel_order_by_sn(db: AsyncSession, user_id: int | None, order_sn: str, redis: Redis | None = None) -> Order | None:
    async with db.begin():
        stmt = (
            select(Order)
            .where(Order.order_sn == order_sn)
            .with_for_update()
            .options(selectinload(Order.items))
        )
        if user_id is not None:
            stmt = stmt.where(Order.user_id == user_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            return None
        if order.status != OrderStatus.pending:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有待支付的订单才能取消")

        sku_ids = [item.sku_id for item in order.items]
        sku_result = await db.execute(select(CourseSKU).where(CourseSKU.id.in_(sku_ids)).with_for_update())
        sku_map = {sku.id: sku for sku in sku_result.scalars().all()}
        for item in order.items:
            sku_map[item.sku_id].stock += item.quantity
        order.status = OrderStatus.cancelled

        # Restore Redis seckill stock if this was a seckill order
        if redis is not None and order.seckill_activity_id is not None:
            await redis.incr(f"seckill:stock:{order.seckill_activity_id}")
            await redis.srem(f"seckill:purchased:{order.seckill_activity_id}", order.user_id)

    result = await db.execute(
        select(Order)
        .where(Order.order_sn == order_sn)
        .options(selectinload(Order.items).selectinload(OrderItem.sku).selectinload(CourseSKU.course))
    )
    return result.scalar_one()


async def cancel_expired_pending_orders(db: AsyncSession, redis: Redis | None = None) -> int:
    result = await db.execute(
        select(Order.order_sn).where(Order.status == OrderStatus.pending, Order.expire_time <= datetime.now())
    )
    order_sns = list(result.scalars().all())
    await db.commit()  # Commit implicit autobegin so cancel_order_by_sn's db.begin() starts a real transaction
    cancelled_count = 0
    for order_sn in order_sns:
        try:
            await cancel_order_by_sn(db, None, order_sn, redis=redis)
            cancelled_count += 1
        except Exception as e:
            print(f"Failed to cancel expired order {order_sn}: {e}")
            # Fallback: force-cancel without stock restoration
            try:
                result = await db.execute(select(Order).where(Order.order_sn == order_sn).with_for_update())
                order = result.scalar_one_or_none()
                if order is not None and order.status == OrderStatus.pending:
                    order.status = OrderStatus.cancelled
                    await db.commit()
                    print(f"Force-cancelled expired order {order_sn}")
                    cancelled_count += 1
            except Exception as e2:
                print(f"Force-cancel also failed for {order_sn}: {e2}")
                await db.rollback()
        finally:
            await db.commit()
    return cancelled_count
