import json
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin, get_current_user
from app.database import get_db, get_redis
from app.models import CourseSKU, Order, OrderItem, OrderStatus, SeckillActivity, SeckillStatus, SKUStatus, User
from app.schemas import (
    SeckillActivityCreate,
    SeckillActivityRead,
    SeckillPreheatResponse,
    SeckillQueueResponse,
    SeckillResultResponse,
)
from app.utils.rate_limiter import allow_token_bucket, allow_user_once_per_second

router = APIRouter()

SECKILL_QUEUE_KEY = "seckill:queue"
STOCK_KEY = "seckill:stock:{activity_id}"
PURCHASED_KEY = "seckill:purchased:{activity_id}"
RESULT_KEY = "seckill:result:{queue_id}"
TOKEN_BUCKET_KEY = "rate:bucket:seckill:{activity_id}"

DECR_STOCK_SCRIPT = """
local stock_key = KEYS[1]
local stock = tonumber(redis.call('GET', stock_key) or '-1')
if stock <= 0 then
    return -1
end
return redis.call('DECR', stock_key)
"""


@router.post("/activities", response_model=SeckillActivityRead)
async def create_seckill_activity(
    payload: SeckillActivityCreate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SeckillActivityRead:
    sku = await db.get(CourseSKU, payload.sku_id)
    if sku is None or sku.status != SKUStatus.on:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU 不可用")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的活动时间范围")

    activity = SeckillActivity(**payload.model_dump())
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return SeckillActivityRead.model_validate(activity)


@router.post("/preheat/{activity_id}", response_model=SeckillPreheatResponse)
async def preheat_seckill_stock(
    activity_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SeckillPreheatResponse:
    activity = await db.get(SeckillActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="秒杀活动不存在")

    await redis.set(STOCK_KEY.format(activity_id=activity.id), activity.stock)
    # 预热只加载 Redis 库存,不改变活动状态。
    # 状态在活动开始时间到达后由抢购请求惰性激活,避免"预热即 active"导致活动提前可见/可抢。
    await db.commit()
    return SeckillPreheatResponse(activity_id=activity.id, stock=activity.stock, message="预热成功")


@router.post("/{activity_id}", response_model=SeckillQueueResponse)
async def submit_seckill(
    activity_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SeckillQueueResponse:
    if not await allow_token_bucket(redis, TOKEN_BUCKET_KEY.format(activity_id=activity_id), 3000, 3000):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求过于频繁，请稍后重试")
    if not await allow_user_once_per_second(redis, current_user.id, activity_id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="操作过于频繁")

    result = await db.execute(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .options(selectinload(SeckillActivity.sku))
    )
    activity = result.scalar_one_or_none()
    now = datetime.now()
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="秒杀活动不存在")
    if activity.status == SeckillStatus.finished or activity.start_time > now or activity.end_time <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="秒杀活动未开始或已结束")
    if activity.sku.status != SKUStatus.on:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU 不可用")

    # 惰性激活:活动时间已到但状态仍为 pending 时,转为 active
    if activity.status == SeckillStatus.pending:
        activity.status = SeckillStatus.active
        await db.commit()
        await db.refresh(activity)

    purchased_key = PURCHASED_KEY.format(activity_id=activity_id)
    if await redis.sismember(purchased_key, current_user.id):
        # Double-check: user might only have expired/cancelled orders — allow retry
        existing = await db.execute(
            select(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == current_user.id,
                OrderItem.sku_id == activity.sku_id,
                Order.status.in_([OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请勿重复抢购")
        # Stale purchased entry — clean it up
        await redis.srem(purchased_key, current_user.id)

    existing_result = await db.execute(
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == current_user.id,
            OrderItem.sku_id == activity.sku_id,
            Order.status.in_([OrderStatus.pending, OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
        )
        .limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        await redis.sadd(purchased_key, current_user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已购买或已下单该课程")

    stock_key = STOCK_KEY.format(activity_id=activity_id)
    # Auto-preheat if Redis key is missing (e.g. after restart)
    if not await redis.exists(stock_key):
        await redis.set(stock_key, activity.stock)
    stock = await redis.eval(DECR_STOCK_SCRIPT, 1, stock_key)
    if int(stock) < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="秒杀库存不足")

    queue_id = uuid.uuid4().hex
    await redis.setex(
        RESULT_KEY.format(queue_id=queue_id),
        600,
        json.dumps({"status": "queued", "message": "排队中", "user_id": current_user.id}),
    )
    await redis.rpush(
        SECKILL_QUEUE_KEY,
        json.dumps(
            {
                "queue_id": queue_id,
                "activity_id": activity.id,
                "user_id": current_user.id,
            }
        ),
    )
    return SeckillQueueResponse(msg="排队中", queue_id=queue_id)


@router.get("/result/{queue_id}", response_model=SeckillResultResponse)
async def get_seckill_result(
    queue_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SeckillResultResponse:
    raw_result = await redis.get(RESULT_KEY.format(queue_id=queue_id))
    if raw_result is None:
        return SeckillResultResponse(queue_id=queue_id, status="failed", message="排队结果不存在或已过期")
    data = json.loads(raw_result)
    if data.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="秒杀结果不存在")
    data.pop("user_id", None)
    return SeckillResultResponse(queue_id=queue_id, **data)
