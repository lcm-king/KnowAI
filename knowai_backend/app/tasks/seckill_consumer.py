import asyncio
import json
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.crud.order_crud import generate_order_sn
from app.crud.user_course_crud import grant_courses_for_order
from app import database
from app.database import AsyncSessionLocal
from app.models import CourseSKU, CourseStatus, Order, OrderItem, OrderStatus, SeckillActivity, SeckillStatus, SKUStatus

SECKILL_QUEUE_KEY = "seckill:queue"
STOCK_KEY = "seckill:stock:{activity_id}"
PURCHASED_KEY = "seckill:purchased:{activity_id}"
RESULT_KEY = "seckill:result:{queue_id}"
PROCESSING_KEY = "seckill:processing:{worker_id}"
LOCK_KEY = "seckill:lock:{queue_id}"

WORKER_COUNT = 5
LOCK_TTL = 30  # seconds before another worker can claim a stuck item


async def consume_seckill_queue(stop_event: asyncio.Event) -> None:
    while database.redis_client is None and not stop_event.is_set():
        await asyncio.sleep(1)
    if stop_event.is_set():
        return

    workers = [
        asyncio.create_task(_seckill_worker(stop_event, i))
        for i in range(WORKER_COUNT)
    ]
    recovery = asyncio.create_task(_recovery_worker(stop_event))

    await asyncio.gather(*workers, recovery, return_exceptions=True)


async def _seckill_worker(stop_event: asyncio.Event, worker_id: int) -> None:
    redis = database.redis_client
    processing_key = PROCESSING_KEY.format(worker_id=worker_id)
    while not stop_event.is_set():
        try:
            item = await redis.blmove(SECKILL_QUEUE_KEY, processing_key, 5, src="LEFT", dest="RIGHT")
            if item is None:
                continue

            payload = json.loads(item)
            queue_id = payload["queue_id"]

            # Lock: mark item as being processed (with TTL so recovery worker can reclaim on crash)
            await redis.setex(LOCK_KEY.format(queue_id=queue_id), LOCK_TTL, str(worker_id))

            await _process_item(item)

            # Success — clean up lock and processing list
            await redis.delete(LOCK_KEY.format(queue_id=queue_id))
            await redis.lrem(processing_key, 1, item)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Seckill worker [{worker_id}] error: {exc}")
            await asyncio.sleep(1)


async def _recovery_worker(stop_event: asyncio.Event) -> None:
    """Periodically re-queue items stuck in processing lists (worker crashed)."""
    redis = database.redis_client
    while not stop_event.is_set():
        await asyncio.sleep(60)
        if redis is None:
            continue
        try:
            for worker_id in range(WORKER_COUNT + 2):  # check a few extra slots
                key = PROCESSING_KEY.format(worker_id=worker_id)
                items = await redis.lrange(key, 0, -1)
                for raw in items:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        await redis.lrem(key, 1, raw)
                        continue
                    lock_key = LOCK_KEY.format(queue_id=payload["queue_id"])
                    if not await redis.exists(lock_key):
                        # Worker crashed or lock expired — re-queue
                        await redis.rpush(SECKILL_QUEUE_KEY, raw)
                        await redis.lrem(key, 1, raw)
                        print(f"Recovery: re-queued stale item {payload.get('queue_id', '?')}")
        except Exception as exc:
            print(f"Recovery worker error: {exc}")


async def _process_item(raw_item: str) -> None:
    redis = database.redis_client
    if redis is None:
        return

    payload = json.loads(raw_item)
    queue_id = payload["queue_id"]
    activity_id = int(payload["activity_id"])
    user_id = int(payload["user_id"])
    result_key = RESULT_KEY.format(queue_id=queue_id)
    purchased_key = PURCHASED_KEY.format(activity_id=activity_id)

    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                result = await db.execute(
                    select(SeckillActivity)
                    .where(SeckillActivity.id == activity_id)
                    .with_for_update()
                    .options(selectinload(SeckillActivity.sku).selectinload(CourseSKU.course))
                )
                activity = result.scalar_one_or_none()
                now = datetime.now()
                if activity is None:
                    raise ValueError("秒杀活动不存在")
                if activity.status != SeckillStatus.active or activity.start_time > now or activity.end_time <= now:
                    raise ValueError("秒杀活动未开始或已结束")
                if activity.sku.status != SKUStatus.on:
                    raise ValueError("SKU 不可用")
                if activity.sku.course is None or activity.sku.course.status != CourseStatus.published:
                    raise ValueError("课程不存在或已下架")

                # Check duplicate purchase (only paid/learning/completed orders block)
                existing_result = await db.execute(
                    select(OrderItem.id)
                    .join(Order, Order.id == OrderItem.order_id)
                    .where(
                        Order.user_id == user_id,
                        OrderItem.sku_id == activity.sku_id,
                        Order.status.in_([OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
                    )
                    .limit(1)
                )
                if existing_result.scalar_one_or_none() is not None:
                    await redis.sadd(purchased_key, user_id)
                    raise ValueError("已购买该课程")

                # Check & decrement SKU stock
                sku_result = await db.execute(select(CourseSKU).where(CourseSKU.id == activity.sku_id).with_for_update())
                sku = sku_result.scalar_one()
                # stock == 0 means unlimited (same as regular order logic)
                if sku.stock > 0 and sku.stock < activity.limit_quantity:
                    raise ValueError("SKU 库存不足")
                if sku.stock > 0:
                    sku.stock -= activity.limit_quantity

                # Decrement seckill activity stock (DB-side tracking)
                activity.stock -= activity.limit_quantity

                # Create order
                order = Order(
                    user_id=user_id,
                    order_sn=generate_order_sn(),
                    total_amount=activity.seckill_price,
                    pay_amount=activity.seckill_price,
                    status=OrderStatus.paid if activity.seckill_price == 0 else OrderStatus.pending,
                    pay_time=datetime.now() if activity.seckill_price == 0 else None,
                    expire_time=datetime.now() + timedelta(minutes=settings.order_expire_minutes),
                    seckill_activity_id=activity.id,
                )
                db.add(order)
                await db.flush()
                db.add(
                    OrderItem(
                        order_id=order.id,
                        sku_id=activity.sku_id,
                        quantity=activity.limit_quantity,
                        price=activity.seckill_price,
                    )
                )
                await db.flush()
                if activity.seckill_price == 0:
                    await grant_courses_for_order(db, order)

            # Outside transaction: mark purchased & write result
            await redis.sadd(purchased_key, user_id)
            if order.status == OrderStatus.pending:
                await redis.setex(f"order:delay:{order.order_sn}", settings.order_expire_minutes * 60, "1")
            await redis.setex(
                result_key,
                600,
                json.dumps({"status": "success", "order_sn": order.order_sn, "message": "秒杀成功", "user_id": user_id}),
            )
            print(f"Seckill success: order={order.order_sn} user={user_id} activity={activity_id}")
    except (ValueError, HTTPException) as exc:
        # Restore Redis stock on failure (atomic DECR was already applied)
        await redis.incr(STOCK_KEY.format(activity_id=activity_id))
        await redis.setex(result_key, 600, json.dumps({"status": "failed", "message": str(exc), "user_id": user_id}))
        print(f"Seckill failed: user={user_id} activity={activity_id} reason={exc}")
