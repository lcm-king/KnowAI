from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.crud import cart_crud
from app.database import get_db, get_redis
from app.models import CourseSKU, SKUStatus, User
from app.schemas import CartAddRequest, CartItemRead, CartMergeRequest, CartRead, CartRemoveRequest, CartUpdateRequest

router = APIRouter()


async def get_active_sku_or_404(db: AsyncSession, sku_id: int) -> CourseSKU:
    result = await db.execute(
        select(CourseSKU)
        .where(CourseSKU.id == sku_id, CourseSKU.status == SKUStatus.on)
        .options(selectinload(CourseSKU.course))
    )
    sku = result.scalar_one_or_none()
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU 不存在或不可用")
    return sku


async def build_cart_response(db: AsyncSession, cart_items: dict[int, dict]) -> CartRead:
    if not cart_items:
        return CartRead(total=0, items=[])

    result = await db.execute(
        select(CourseSKU)
        .where(CourseSKU.id.in_(cart_items.keys()))
        .options(selectinload(CourseSKU.course))
    )
    skus = result.scalars().all()
    sku_map = {sku.id: sku for sku in skus}
    items: list[CartItemRead] = []
    for sku_id, item in sorted(cart_items.items(), key=lambda pair: pair[1]["add_time"], reverse=True):
        sku = sku_map.get(sku_id)
        if sku is None:
            continue
        items.append(
            CartItemRead(
                sku_id=sku.id,
                course_id=sku.course_id,
                course_title=sku.course.title,
                cover=sku.course.cover,
                sku_name=sku.sku_name,
                price=sku.price,
                quantity=item["quantity"],
                selected=item["selected"],
                add_time=item["add_time"],
            )
        )
    return CartRead(total=len(items), items=items)


@router.post("/add")
async def add_to_cart(
    item: CartAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    await get_active_sku_or_404(db, item.sku_id)
    added = await cart_crud.add_cart_item(redis, current_user.id, item.sku_id, item.quantity)
    if not added:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该商品已在购物车中")
    return {"message": "添加成功"}


@router.put("/update")
async def update_cart(
    item: CartUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    updated = await cart_crud.update_cart_item(redis, current_user.id, item.sku_id, item.quantity, item.selected)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购物车中未找到该商品")
    return {"message": "更新成功"}


@router.delete("/remove")
async def remove_from_cart(
    item: CartRemoveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    removed = await cart_crud.remove_cart_item(redis, current_user.id, item.sku_id)
    if removed == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购物车中未找到该商品")
    return {"message": "删除成功"}


@router.delete("/clear")
async def clear_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    await cart_crud.clear_cart(redis, current_user.id)
    return {"message": "已清空"}


@router.get("", response_model=CartRead)
async def get_cart(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> CartRead:
    cart_items = await cart_crud.get_cart_items(redis, current_user.id)
    return await build_cart_response(db, cart_items)


@router.post("/merge")
async def merge_cart(
    payload: CartMergeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, int]:
    if not payload.items:
        return {"merged_count": 0}

    sku_ids = [item.sku_id for item in payload.items]
    result = await db.execute(select(CourseSKU.id).where(CourseSKU.id.in_(sku_ids), CourseSKU.status == SKUStatus.on))
    active_sku_ids = set(result.scalars().all())
    valid_items = [item.model_dump() for item in payload.items if item.sku_id in active_sku_ids]
    merged_count = await cart_crud.merge_cart_items(redis, current_user.id, valid_items)
    return {"merged_count": merged_count}
