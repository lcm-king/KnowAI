import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import close_connections, init_db, init_mongo, init_redis
from app.routers import admin, ai, ai_new, auth, cart, courses, favorite, orders, pay, reviews, search, seckill, teacher, teacher_seckill, upload
from app.tasks.order_expire import scan_expired_orders
from app.tasks.seckill_consumer import consume_seckill_queue
from app.tasks.seckill_expire import finish_expired_seckills


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_mongo()
    await init_redis()
    stop_event = asyncio.Event()
    expire_task = asyncio.create_task(scan_expired_orders(stop_event))
    seckill_task = asyncio.create_task(consume_seckill_queue(stop_event))
    seckill_expire_task = asyncio.create_task(finish_expired_seckills(stop_event))
    yield
    stop_event.set()
    await expire_task
    await seckill_task
    await seckill_expire_task
    await close_connections()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Auth"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])
app.include_router(courses.router, prefix=f"{settings.api_prefix}/courses", tags=["Courses"])
app.include_router(teacher.router, prefix=f"{settings.api_prefix}/teacher", tags=["Teacher"])
app.include_router(search.router, prefix=f"{settings.api_prefix}/search", tags=["Search"])
app.include_router(cart.router, prefix=f"{settings.api_prefix}/cart", tags=["Cart"])
app.include_router(orders.router, prefix=f"{settings.api_prefix}/orders", tags=["Orders"])
app.include_router(pay.router, prefix=f"{settings.api_prefix}/pay", tags=["Pay"])
app.include_router(seckill.router, prefix=f"{settings.api_prefix}/seckill", tags=["Seckill"])
app.include_router(teacher_seckill.router, prefix=f"{settings.api_prefix}/teacher", tags=["Teacher Seckill"])
app.include_router(favorite.router, prefix=f"{settings.api_prefix}/favorites", tags=["Favorites"])
app.include_router(ai.router, prefix=f"{settings.api_prefix}/ai", tags=["AI (deprecated)"])
# New AI endpoints (LangChain + LangGraph)
app.include_router(ai_new.router, prefix=f"{settings.api_prefix}/ai", tags=["AI"])
app.include_router(reviews.router, prefix=f"{settings.api_prefix}/courses", tags=["Course Reviews"])
app.include_router(upload.router, prefix=f"{settings.api_prefix}/upload", tags=["Upload"])

# Mount uploads directory for serving static files
uploads_dir = settings.upload_dir
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount(f"{settings.api_prefix}/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "KnowAI API running"}
