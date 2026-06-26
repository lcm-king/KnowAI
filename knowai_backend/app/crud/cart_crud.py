import json
import time
from typing import Any

from redis.asyncio import Redis


def get_cart_key(user_id: int) -> str:
    return f"plan:{user_id}"


def normalize_quantity(quantity: int) -> int:
    return 1 if quantity >= 1 else 0


def dumps_item(quantity: int = 1, selected: bool = True, add_time: int | None = None) -> str:
    return json.dumps(
        {
            "quantity": normalize_quantity(quantity),
            "selected": selected,
            "add_time": add_time or int(time.time()),
        },
        ensure_ascii=False,
    )


def loads_item(value: str) -> dict[str, Any]:
    data = json.loads(value)
    return {
        "quantity": normalize_quantity(int(data.get("quantity", 1))),
        "selected": bool(data.get("selected", True)),
        "add_time": int(data.get("add_time", time.time())),
    }


async def add_cart_item(redis: Redis, user_id: int, sku_id: int, quantity: int = 1) -> bool:
    key = get_cart_key(user_id)
    field = str(sku_id)
    if await redis.hexists(key, field):
        return False
    await redis.hset(key, field, dumps_item(quantity=quantity, selected=True))
    return True


async def update_cart_item(
    redis: Redis,
    user_id: int,
    sku_id: int,
    quantity: int | None = None,
    selected: bool | None = None,
) -> dict[str, Any] | None:
    key = get_cart_key(user_id)
    field = str(sku_id)
    value = await redis.hget(key, field)
    if value is None:
        return None

    item = loads_item(value)
    if quantity is not None:
        item["quantity"] = normalize_quantity(quantity)
    if selected is not None:
        item["selected"] = selected
    await redis.hset(key, field, json.dumps(item, ensure_ascii=False))
    return item


async def remove_cart_item(redis: Redis, user_id: int, sku_id: int) -> int:
    return await redis.hdel(get_cart_key(user_id), str(sku_id))


async def clear_cart(redis: Redis, user_id: int) -> int:
    return await redis.delete(get_cart_key(user_id))


async def get_cart_items(redis: Redis, user_id: int) -> dict[int, dict[str, Any]]:
    data = await redis.hgetall(get_cart_key(user_id))
    return {int(sku_id): loads_item(value) for sku_id, value in data.items()}


async def merge_cart_items(redis: Redis, user_id: int, items: list[dict[str, Any]]) -> int:
    key = get_cart_key(user_id)
    merged_count = 0
    for item in items:
        sku_id = int(item["sku_id"])
        field = str(sku_id)
        if await redis.hexists(key, field):
            continue
        await redis.hset(
            key,
            field,
            dumps_item(
                quantity=int(item.get("quantity", 1)),
                selected=bool(item.get("selected", True)),
                add_time=int(item.get("add_time", time.time())),
            ),
        )
        merged_count += 1
    return merged_count
