from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, get_redis
from app.models import User, UserRole
from app.schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_token_key(user_id: int, jti: str) -> str:
    return f"token:{user_id}:{jti}"


def create_access_token(subject: str | int, jti: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(subject), "jti": jti, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def create_user_access_token(user: User, redis: Redis) -> str:
    jti = uuid4().hex
    token = create_access_token(user.id, jti)
    await redis.set(get_token_key(user.id, jti), "1", ex=settings.access_token_expire_seconds)
    return token


async def revoke_access_token(token: str, redis: Redis) -> None:
    payload = decode_token(token)
    await redis.delete(get_token_key(payload.user_id, payload.jti))


async def revoke_all_user_tokens(user_id: int, redis: Redis) -> int:
    """Delete all active tokens for a user. Returns count of deleted keys."""
    pattern = f"token:{user_id}:*"
    cursor = b"0"
    deleted = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            deleted += await redis.delete(*keys)
        if cursor in (b"0", 0):
            break
    return deleted


def decode_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="身份验证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id is None or jti is None:
            raise credentials_exception
        return TokenData(user_id=int(user_id), jti=jti)
    except (JWTError, ValueError):
        raise credentials_exception


async def authenticate_user(db: AsyncSession, account: str, password: str) -> User | None:
    result = await db.execute(
        select(User).where(or_(User.username == account, User.phone == account, User.email == account))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    token_data = decode_token(token)
    if await redis.exists(get_token_key(token_data.user_id, token_data.jti)) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已被撤销",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份验证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_teacher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要教师权限")
    return current_user


async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> User | None:
    """尝试获取当前用户，未登录时返回 None。"""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, token = get_authorization_scheme_param(authorization)
    if not token or scheme.lower() != "bearer":
        return None
    try:
        token_data = decode_token(token)
        if await redis.exists(get_token_key(token_data.user_id, token_data.jti)) == 0:
            return None
        result = await db.execute(select(User).where(User.id == token_data.user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None
