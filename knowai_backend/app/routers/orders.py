from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import cart_crud, order_crud
from app.database import get_db, get_redis
from app.models import Order, OrderItem, OrderStatus, User
from app.schemas import OrderCreate, OrderCreateResponse, OrderItemOut, OrderListResponse, OrderOut

router = APIRouter()


def serialize_order(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        order_sn=order.order_sn,
        total_amount=order.total_amount,
        pay_amount=order.pay_amount,
        status=order.status,
        expire_time=order.expire_time,
        pay_time=order.pay_time,
        created_at=order.created_at,
        items=[serialize_order_item(item) for item in order.items],
    )


def serialize_order_item(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        id=item.id,
        sku_id=item.sku_id,
        quantity=item.quantity,
        price=item.price,
        course_title=item.sku.course.title if item.sku and item.sku.course else None,
        sku_name=item.sku.sku_name if item.sku else None,
    )


@router.post("/create", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> OrderCreateResponse:
    orders = await order_crud.create_orders(db, redis, current_user.id, order_in.sku_ids, order_in.address_id)
    for sku_id in order_in.sku_ids:
        await cart_crud.remove_cart_item(redis, current_user.id, sku_id)
    order_sns = [o.order_sn for o in orders]
    all_free = all(o.total_amount == 0 for o in orders)
    total = sum(o.total_amount for o in orders)
    return OrderCreateResponse(
        order_sn=order_sns[0],
        order_sns=order_sns,
        total_amount=total,
        expire_time=orders[0].expire_time,
        direct_granted=all_free,
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
) -> OrderListResponse:
    total, orders = await order_crud.list_user_orders(db, current_user.id, page, page_size, status_filter)
    return OrderListResponse(total=total, items=[serialize_order(order) for order in orders])


@router.get("/{order_sn}", response_model=OrderOut)
async def get_order_detail(
    order_sn: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderOut:
    order = await order_crud.get_user_order(db, current_user.id, order_sn)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return serialize_order(order)


@router.post("/{order_sn}/cancel", response_model=OrderOut)
async def cancel_order(
    order_sn: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> OrderOut:
    order = await order_crud.cancel_order_by_sn(db, current_user.id, order_sn, redis=redis)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    await redis.delete(f"order:delay:{order.order_sn}")
    return serialize_order(order)
