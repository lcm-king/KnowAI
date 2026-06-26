from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate_user, create_user_access_token, get_current_user, get_password_hash, revoke_access_token, verify_password
from app.config import settings
from app.database import get_db, get_redis
from app.models import Teacher, TeacherStatus, User, UserRole
from app.schemas import ApplyTeacherRequest, PhoneCodeLogin, RegisterResponse, SendCodeRequest, Token, UserCreate, UserLogin, UserRead

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")
CODE_TTL = 300  # 5 minutes
CODE_PREFIX = "verify:code:"


import random

from app.services.cloopen_sms import get_sms_client


@router.post("/send-code")
async def send_code(
    request: SendCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    # 检查手机号/邮箱是否已被注册
    existing = await db.execute(
        select(User).where(
            or_(User.phone == request.target, User.email == request.target)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号或邮箱已被注册",
        )

    code = str(random.randint(1000, 9999))
    key = f"{CODE_PREFIX}{request.target}"
    await redis.setex(key, CODE_TTL, code)

    # Try real SMS first
    sms = get_sms_client()
    if sms and sms.enabled and settings.sms_mock is False:
        try:
            await sms.send(request.target, (code, "5"))
            return {"message": "验证码已发送"}
        except Exception as e:
            print(f"SMS send failed: {e}")

    # Fallback: return code in response (dev/mock mode)
    return {"message": "验证码已发送", "code": code}


@router.post("/send-login-code")
async def send_login_code(
    request: SendCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    """发送登录验证码 — 手机号必须已注册。"""
    existing = await db.execute(
        select(User).where(User.phone == request.target)
    )
    if existing.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该手机号未注册",
        )

    code = str(random.randint(1000, 9999))
    key = f"{CODE_PREFIX}{request.target}"
    await redis.setex(key, CODE_TTL, code)

    sms = get_sms_client()
    if sms and sms.enabled and settings.sms_mock is False:
        try:
            await sms.send(request.target, (code, "5"))
            return {"message": "验证码已发送"}
        except Exception as e:
            print(f"SMS send failed: {e}")

    return {"message": "验证码已发送", "code": code}


@router.post("/login/phone", response_model=Token)
async def login_by_phone(
    payload: PhoneCodeLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> Token:
    """手机号 + 验证码登录。"""
    code_key = f"{CODE_PREFIX}{payload.phone}"
    stored_code = await redis.get(code_key)
    if stored_code is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取")
    if stored_code != payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误")
    await redis.delete(code_key)

    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被封禁，请联系管理员")

    return Token(access_token=await create_user_access_token(user, redis))


@router.post("/apply-teacher")
async def apply_teacher(
    payload: ApplyTeacherRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """普通用户申请成为讲师（等待管理员审核）。"""
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有学生角色可以申请成为讲师")

    existing = await db.execute(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已提交过讲师申请，请等待审核")

    teacher = Teacher(
        user_id=current_user.id,
        name=payload.name,
        bio=payload.bio,
        status=TeacherStatus.pending,
    )
    db.add(teacher)
    await db.flush()
    current_user.teacher_id = teacher.id
    await db.commit()

    return {"message": "讲师申请已提交，等待管理员审核"}


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> RegisterResponse:
    # Determine which field was used to send the code
    target = user_in.phone or user_in.email
    code_key = f"{CODE_PREFIX}{target}"
    stored_code = await redis.get(code_key)
    if stored_code is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取")
    if stored_code != user_in.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误")
    await redis.delete(code_key)  # 用完即删

    result = await db.execute(
        select(User).where(or_(User.username == user_in.username, User.phone == user_in.phone, User.email == user_in.email))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名、手机或邮箱已存在")

    user = User(
        username=user_in.username,
        phone=user_in.phone,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=UserRole.student,
    )
    db.add(user)
    await db.commit()

    return RegisterResponse(message="注册成功，请登录")


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> Token:
    user = await authenticate_user(db, user_in.account, user_in.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员",
        )
    return Token(access_token=await create_user_access_token(user, redis))


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    await revoke_access_token(token, redis)
    return {"message": "退出成功"}


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, str]:
    password = payload.get("password", "")
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码以确认注销")
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码错误，无法注销")

    # 软删除：禁用账号、清除敏感信息、保留订单数据
    current_user.is_active = False
    current_user.username = f"deleted_{current_user.id}"
    current_user.phone = f"deleted_{current_user.id}"
    current_user.email = f"deleted_{current_user.id}@knowai.local"
    current_user.password_hash = "DISABLED"
    await db.commit()

    # 撤销当前 token
    await revoke_access_token(token, redis)
    return {"message": "账号已注销"}
