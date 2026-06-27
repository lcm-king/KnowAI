import random
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.crud.user_course_crud import grant_courses_for_order
from app.models import Course, CourseSKU, CourseStatus, Order, OrderItem, OrderStatus, SeckillActivity, SKUStatus

LOCK_EXPIRE_SECONDS = 30

# Lua: 仅当锁持有者 token 匹配时才删除,防止误删别人的锁
_RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


def generate_order_sn() -> str:
    return f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}{random.randint(1000, 9999)}"[:32]


def lock_key(sku_id: int) -> str:
    return f"lock:order:{sku_id}"


async def acquire_sku_locks(redis: Redis, sku_ids: list[int]) -> list[tuple[str, str]]:
    """获取 SKU 分布式锁,返回 (key, token) 列表以便安全释放。"""
    acquired: list[tuple[str, str]] = []
    for sku_id in sorted(set(sku_ids)):
        key = lock_key(sku_id)
        token = secrets.token_hex(16)
        locked = await redis.set(key, token, nx=True, ex=LOCK_EXPIRE_SECONDS)
        if not locked:
            # 释放已获取的锁
            for k, t in acquired:
                await redis.eval(_RELEASE_LOCK_SCRIPT, 1, k, t)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="当前购买人数过多，请稍后重试")
        acquired.append((key, token))
    return acquired


async def release_sku_locks(redis: Redis, locks: list[tuple[str, str]]) -> None:
    for key, token in locks:
        await redis.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)


async def create_orders(db: AsyncSession, redis: Redis, user_id: int, sku_ids: list[int], address_id: int | None) -> list[Order]:
    """Create one or more orders, grouped by teacher."""
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

        # Group SKUs by teacher
        teacher_groups: dict[int, list[int]] = {}
        for sku_id in sku_ids:
            teacher_id = sku_map[sku_id].course.teacher_id
            teacher_groups.setdefault(teacher_id, []).append(sku_id)

        orders: list[Order] = []
        for teacher_id, t_sku_ids in teacher_groups.items():
            total_amount = sum((sku_map[sid].price for sid in t_sku_ids), Decimal("0.00"))
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

            for sku_id in t_sku_ids:
                db.add(OrderItem(order_id=order.id, sku_id=sku_id, quantity=1, price=sku_map[sku_id].price))

            orders.append(order)

        await db.commit()

        # Auto-grant free orders; set delay for paid ones
        has_free = False
        for order in orders:
            await db.refresh(order)
            if order.total_amount == 0:
                has_free = True
                order.status = OrderStatus.paid
                order.pay_time = datetime.now()
                await grant_courses_for_order(db, order, redis=redis)
            else:
                await redis.setex(f"order:delay:{order.order_sn}", settings.order_expire_minutes * 60, "1")

        if has_free:
            await db.commit()
            for order in orders:
                await db.refresh(order)

        return orders
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
            if item.sku_id in sku_map:
                sku_map[item.sku_id].stock += item.quantity
        order.status = OrderStatus.cancelled

        # Restore seckill stock (DB activity.stock + Redis remaining + purchased set)
        if order.seckill_activity_id is not None:
            activity_result = await db.execute(
                select(SeckillActivity).where(SeckillActivity.id == order.seckill_activity_id).with_for_update()
            )
            activity = activity_result.scalar_one_or_none()
            if activity is not None:
                total_qty = sum(item.quantity for item in order.items)
                activity.stock += total_qty
            if redis is not None:
                total_qty = sum(item.quantity for item in order.items)
                await redis.incrby(f"seckill:stock:{order.seckill_activity_id}", total_qty)
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
            await db.rollback()
    return cancelled_count
