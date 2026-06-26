from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_teacher
from app.crud import course_crud
from app.database import get_db
from app.models import (
    Course,
    CourseSKU,
    CourseStatus,
    SeckillActivity,
    SeckillStatus,
    SKUStatus,
    User,
)
from app.schemas import SeckillActivityCreate

router = APIRouter()


async def get_teacher_or_404(db: AsyncSession, user: User):
    teacher = await course_crud.get_teacher_by_user_id(db, user.id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师信息不存在")
    return teacher


@router.get("/skus")
async def list_teacher_skus(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> list[dict]:
    """获取讲师所有课程的 SKU 列表（用于秒杀请求时选择）"""
    teacher = await get_teacher_or_404(db, current_user)
    stmt = (
        select(CourseSKU)
        .join(Course, Course.id == CourseSKU.course_id)
        .where(
            Course.teacher_id == teacher.id,
            Course.status.in_([CourseStatus.published, CourseStatus.pending]),
            CourseSKU.status == SKUStatus.on,
        )
        .options(selectinload(CourseSKU.course))
    )
    result = await db.execute(stmt)
    skus = result.scalars().all()
    return [
        {
            "id": sku.id,
            "sku_name": sku.sku_name or sku.course.title,
            "price": str(sku.price),
            "stock": sku.stock,
            "course_id": sku.course_id,
            "course_title": sku.course.title,
        }
        for sku in skus
    ]


@router.post("/seckills", status_code=status.HTTP_201_CREATED)
async def create_seckill_request(
    payload: SeckillActivityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> dict:
    """讲师创建秒杀请求（状态为 pending，等待管理员审批）"""
    teacher = await get_teacher_or_404(db, current_user)

    # 验证 SKU 属于该讲师
    sku = await db.get(CourseSKU, payload.sku_id)
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU 不存在")
    course = await db.get(Course, sku.course_id)
    if course is None or course.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    if sku.status != SKUStatus.on:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU 不可用")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="活动结束时间必须晚于开始时间")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的活动时间范围")

    activity = SeckillActivity(
        sku_id=payload.sku_id,
        seckill_price=payload.seckill_price,
        stock=payload.stock,
        limit_quantity=payload.limit_quantity,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=SeckillStatus.pending,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return {
        "id": activity.id,
        "sku_id": activity.sku_id,
        "course_title": course.title,
        "seckill_price": str(activity.seckill_price),
        "stock": activity.stock,
        "start_time": activity.start_time.isoformat(),
        "end_time": activity.end_time.isoformat(),
        "status": activity.status.value,
        "created_at": activity.created_at.isoformat(),
    }


@router.get("/seckills")
async def list_teacher_seckills(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    """获取讲师的所有秒杀请求"""
    teacher = await get_teacher_or_404(db, current_user)

    # 查找该讲师所有课程下的秒杀活动
    course_ids_stmt = select(Course.id).where(Course.teacher_id == teacher.id)
    course_ids = {row[0] for row in (await db.execute(course_ids_stmt)).all()}

    sku_ids_stmt = select(CourseSKU.id).where(CourseSKU.course_id.in_(course_ids))
    sku_ids = {row[0] for row in (await db.execute(sku_ids_stmt)).all()}

    if not sku_ids:
        return {"total": 0, "items": []}

    stmt = (
        select(SeckillActivity)
        .where(SeckillActivity.sku_id.in_(sku_ids))
        .options(selectinload(SeckillActivity.sku).selectinload(CourseSKU.course))
        .order_by(SeckillActivity.created_at.desc())
    )
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()

    return {
        "total": int(total or 0),
        "items": [
            {
                "id": a.id,
                "sku_id": a.sku_id,
                "course_title": a.sku.course.title if a.sku and a.sku.course else "未知课程",
                "seckill_price": str(a.seckill_price),
                "stock": a.stock,
                "start_time": a.start_time.isoformat(),
                "end_time": a.end_time.isoformat(),
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in items
        ],
    }
