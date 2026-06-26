import asyncio

from app.crud.order_crud import cancel_expired_pending_orders
from app.database import AsyncSessionLocal, redis_client


async def scan_expired_orders(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                cancelled_count = await cancel_expired_pending_orders(db, redis=redis_client)
                if cancelled_count:
                    print(f"Cancelled {cancelled_count} expired orders")
        except Exception as e:
            print(f"Order expiry scan failed: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            continue
