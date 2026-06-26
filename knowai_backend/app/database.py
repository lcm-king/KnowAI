from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis, from_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base

engine = create_async_engine(settings.mysql_url, echo=settings.debug, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

mongo_client: AsyncIOMotorClient | None = None
redis_client: Redis | None = None


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: make user_courses.expire_date nullable for permanent access
        await conn.execute(
            text("ALTER TABLE user_courses MODIFY COLUMN expire_date DATETIME NULL")
        )
        # Create course_reviews table (idempotent)
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS course_reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    course_id INT NOT NULL,
                    user_id INT NOT NULL,
                    rating INT NOT NULL,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_course_user_review (course_id, user_id)
                )
            """)
        )
        # Create lesson_knowledge table (idempotent)
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS lesson_knowledge (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    lesson_id INT NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_url VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    file_size INT DEFAULT 0,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
            """)
        )
        # Create course_knowledge table (idempotent)
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS course_knowledge (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    course_id INT NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_url VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    file_size INT DEFAULT 0,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)
        )
        # Migration: add seckill_activity_id to orders
        result = await conn.execute(text("SHOW COLUMNS FROM orders LIKE 'seckill_activity_id'"))
        if not result.fetchone():
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN seckill_activity_id INT NULL, ADD FOREIGN KEY fk_seckill_activity (seckill_activity_id) REFERENCES seckill_activities(id) ON DELETE SET NULL")
            )

        # Create knowledge_vectors table (idempotent)
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS knowledge_vectors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    course_id INT NULL,
                    lesson_id INT NULL,
                    file_id INT NOT NULL,
                    file_type VARCHAR(20) NOT NULL,
                    chunk_count INT DEFAULT 0,
                    vector_store_id VARCHAR(100) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
            """)
        )


async def init_mongo() -> None:
    global mongo_client
    mongo_client = AsyncIOMotorClient(settings.mongo_url)
    db = mongo_client[settings.mongo_db_name]
    await db.users.create_index("username", unique=True)
    await db.users.create_index("phone", unique=True)
    await db.users.create_index("email", unique=True)
    await db.chat_messages.create_index([("user_id", 1), ("session_id", 1), ("created_at", 1)])


async def init_redis() -> None:
    global redis_client
    redis_client = from_url(settings.redis_url, decode_responses=True)


async def close_connections() -> None:
    if mongo_client is not None:
        mongo_client.close()
    if redis_client is not None:
        await redis_client.aclose()
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_mongo() -> AsyncIOMotorDatabase:
    if mongo_client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return mongo_client[settings.mongo_db_name]


async def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client
