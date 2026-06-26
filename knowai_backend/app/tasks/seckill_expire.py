import asyncio
from datetime import datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import SeckillActivity, SeckillStatus


async def finish_expired_seckills(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SeckillActivity)
                .where(SeckillActivity.status == SeckillStatus.active, SeckillActivity.end_time <= datetime.now())
            )
            expired = list(result.scalars().all())
            for activity in expired:
                activity.status = SeckillStatus.finished
            if expired:
                await db.commit()
                print(f"Finished {len(expired)} expired seckill activities")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            continue
