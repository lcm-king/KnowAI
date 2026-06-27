from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_admin
from app.crud import course_crud, user_crud
from app.database import get_db, get_redis
from app.tasks.sync_es import delete_course_from_es, sync_course_to_es
from app.models import (
    Chapter,
    Course,
    CourseKnowledge,
    CourseReview,
    CourseSKU,
    CourseStatus,
    Lesson,
    Order,
    OrderStatus,
    SeckillActivity,
    SeckillStatus,
    Teacher,
    TeacherStatus,
    User,
    UserRole,
)
from app.schemas import (
    AdminCourseApprovalListResponse,
    AdminCourseApprovalOut,
    AdminCourseCreate,
    AdminCourseListResponse,
    AdminReviewListResponse,
    AdminReviewOut,
    AdminSeckillApprovalListResponse,
    AdminSeckillApprovalOut,
    AdminTeacherApprovalListResponse,
    AdminTeacherApprovalOut,
    AdminUserListResponse,
    AdminUserOut,
    AdminUserStatusUpdate,
    CourseKnowledgeRead,
    CourseRead,
    OrderItemOut,
    OrderListResponse,
    OrderOut,
    ReviewRead,
)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard")
async def dashboard(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    total_users = await db.scalar(select(func.count()).select_from(User))
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_registrations = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today_start)
    )
    total_teachers = await db.scalar(select(func.count()).select_from(Teacher))
    pending_teachers = await db.scalar(
        select(func.count()).select_from(Teacher).where(Teacher.status == TeacherStatus.pending)
    )
    active_courses = await db.scalar(
        select(func.count()).select_from(Course).where(Course.status == CourseStatus.published)
    )
    pending_courses = await db.scalar(
        select(func.count()).select_from(Course).where(Course.status == CourseStatus.pending)
    )
    pending_seckills = await db.scalar(
        select(func.count()).select_from(SeckillActivity).where(SeckillActivity.status == SeckillStatus.pending)
    )
    return {
        "total_users": int(total_users or 0),
        "today_registrations": int(today_registrations or 0),
        "total_teachers": int(total_teachers or 0),
        "pending_teachers": int(pending_teachers or 0),
        "active_courses": int(active_courses or 0),
        "pending_courses": int(pending_courses or 0),
        "pending_seckills": int(pending_seckills or 0),
    }


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    role: UserRole | None = None,
    keyword: str | None = None,
) -> AdminUserListResponse:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            (User.username.like(like)) | (User.phone.like(like)) | (User.email.like(like))
        )
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [AdminUserOut.model_validate(u) for u in result.scalars().all()]
    return AdminUserListResponse(total=int(total or 0), items=items)


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
async def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == current_admin.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能封禁自己")
    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user)


@router.get("/courses/pending", response_model=AdminCourseApprovalListResponse)
async def list_pending_courses(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminCourseApprovalListResponse:
    stmt = (
        select(Course)
        .where(Course.status == CourseStatus.pending)
        .options(selectinload(Course.teacher))
    )
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    result = await db.execute(
        stmt.order_by(Course.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        AdminCourseApprovalOut(
            id=c.id,
            title=c.title,
            teacher_id=c.teacher_id,
            teacher_name=c.teacher.name if c.teacher else None,
            category=c.category,
            total_hours=c.total_hours,
            status=c.status,
            created_at=c.created_at,
        )
        for c in result.scalars().all()
    ]
    return AdminCourseApprovalListResponse(total=int(total or 0), items=items)


@router.post("/courses/{course_id}/approve")
async def approve_course(
    course_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    if course.status != CourseStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程不是待审核状态")
    course.status = CourseStatus.published
    await db.commit()
    await redis.delete("homepage:courses", f"course:detail:{course_id}")
    await sync_course_to_es(course_id, db)
    return {"status": "ok", "course_id": str(course_id), "new_status": CourseStatus.published.value}


@router.post("/courses/{course_id}/reject")
async def reject_course(
    course_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    if course.status != CourseStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程不是待审核状态")
    course.status = CourseStatus.draft
    await db.commit()
    await redis.delete("homepage:courses", f"course:detail:{course_id}")
    await delete_course_from_es(course_id)
    return {"status": "ok", "course_id": str(course_id), "new_status": CourseStatus.draft.value}


@router.get("/seckills/pending", response_model=AdminSeckillApprovalListResponse)
async def list_pending_seckills(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminSeckillApprovalListResponse:
    stmt = select(SeckillActivity).where(SeckillActivity.status == SeckillStatus.pending)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    result = await db.execute(
        stmt.order_by(SeckillActivity.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [AdminSeckillApprovalOut.model_validate(s) for s in result.scalars().all()]
    return AdminSeckillApprovalListResponse(total=int(total or 0), items=items)


@router.post("/seckills/{activity_id}/approve")
async def approve_seckill(
    activity_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    activity = await db.get(SeckillActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="秒杀活动不存在")
    if activity.status != SeckillStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="活动不是待审核状态")
    now = datetime.now()
    if activity.start_time <= now < activity.end_time:
        activity.status = SeckillStatus.active
    elif now >= activity.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="活动已结束")
    else:
        activity.status = SeckillStatus.active
    await db.commit()

    # Preheat stock into Redis so users can seckill immediately
    await redis.set(f"seckill:stock:{activity.id}", activity.stock)

    return {"status": "ok", "activity_id": str(activity_id), "new_status": activity.status.value}


@router.get("/teachers/pending", response_model=AdminTeacherApprovalListResponse)
async def list_pending_teachers(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminTeacherApprovalListResponse:
    stmt = (
        select(Teacher, User)
        .join(User, Teacher.user_id == User.id)
        .where(Teacher.status == TeacherStatus.pending)
    )
    total = await db.scalar(
        select(func.count()).select_from(Teacher).where(Teacher.status == TeacherStatus.pending)
    )
    rows = (
        await db.execute(
            stmt.order_by(Teacher.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        AdminTeacherApprovalOut(
            id=t.id,
            user_id=t.user_id,
            username=u.username,
            phone=u.phone,
            email=u.email,
            name=t.name,
            bio=t.bio,
            created_at=t.created_at,
        )
        for t, u in rows
    ]
    return AdminTeacherApprovalListResponse(total=int(total or 0), items=items)


@router.post("/teachers/{teacher_id}/approve")
async def approve_teacher(
    teacher_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    teacher = await db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="讲师不存在")
    if teacher.status != TeacherStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="讲师不是待审核状态")
    teacher.status = TeacherStatus.approved
    # 同时将用户角色升级为 teacher
    user = await db.get(User, teacher.user_id)
    if user is not None:
        user.role = UserRole.teacher
    await db.commit()
    return {"status": "ok", "teacher_id": str(teacher_id), "new_status": TeacherStatus.approved.value}


@router.post("/teachers/{teacher_id}/reject")
async def reject_teacher(
    teacher_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    teacher = await db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="讲师不存在")
    if teacher.status != TeacherStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="讲师不是待审核状态")
    teacher.status = TeacherStatus.rejected
    await db.commit()
    return {"status": "ok", "teacher_id": str(teacher_id), "new_status": TeacherStatus.rejected.value}


# ── Admin Detail Endpoints ──


@router.get("/teachers/{teacher_id}")
async def admin_get_teacher_detail(
    teacher_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get full teacher detail with user info."""
    result = await db.execute(
        select(Teacher, User)
        .join(User, Teacher.user_id == User.id)
        .where(Teacher.id == teacher_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="讲师不存在")
    t, u = row
    return {
        "id": t.id,
        "user_id": t.user_id,
        "username": u.username,
        "phone": u.phone,
        "email": u.email,
        "name": t.name,
        "bio": t.bio,
        "avatar": t.avatar,
        "status": t.status.value,
        "created_at": t.created_at.isoformat(),
    }


@router.get("/courses/{course_id}/detail")
async def admin_get_course_detail(
    course_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get full course detail with chapters, lessons, SKUs, knowledge files."""
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.teacher),
            selectinload(Course.skus),
            selectinload(Course.chapters).selectinload(Chapter.lessons),
            selectinload(Course.knowledge_files),
        )
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    return {
        "id": course.id,
        "teacher_id": course.teacher_id,
        "teacher_name": course.teacher.name if course.teacher else None,
        "title": course.title,
        "description": course.description,
        "cover": course.cover,
        "category": course.category,
        "total_hours": course.total_hours,
        "learn_count": course.learn_count,
        "rating": course.rating,
        "status": course.status.value,
        "created_at": course.created_at.isoformat(),
        "skus": [
            {
                "id": sku.id,
                "price": str(sku.price),
                "stock": sku.stock,
                "sku_name": sku.sku_name,
                "status": sku.status.value,
            }
            for sku in course.skus
        ],
        "chapters": [
            {
                "id": ch.id,
                "title": ch.title,
                "sort_order": ch.sort_order,
                "lessons": [
                    {
                        "id": le.id,
                        "title": le.title,
                        "video_url": le.video_url,
                        "duration": le.duration,
                        "sort_order": le.sort_order,
                    }
                    for le in ch.lessons
                ],
            }
            for ch in course.chapters
        ],
        "knowledge_files": [
            CourseKnowledgeRead.model_validate(kf).model_dump()
            for kf in course.knowledge_files
        ],
    }


@router.get("/seckills/{activity_id}")
async def admin_get_seckill_detail(
    activity_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get seckill detail with SKU and course info."""
    result = await db.execute(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .options(selectinload(SeckillActivity.sku).selectinload(CourseSKU.course))
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="秒杀活动不存在")

    return {
        "id": activity.id,
        "sku_id": activity.sku_id,
        "seckill_price": str(activity.seckill_price),
        "stock": activity.stock,
        "limit_quantity": activity.limit_quantity,
        "start_time": activity.start_time.isoformat(),
        "end_time": activity.end_time.isoformat(),
        "status": activity.status.value,
        "created_at": activity.created_at.isoformat(),
        "course_id": activity.sku.course_id,
        "course_title": activity.sku.course.title if activity.sku.course else None,
        "sku_price": str(activity.sku.price),
        "sku_name": activity.sku.sku_name,
        "sku_stock": activity.sku.stock,
    }


# ── Admin Course Management ──

@router.get("/courses", response_model=AdminCourseListResponse)
async def admin_list_courses(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: CourseStatus | None = None,
    keyword: str | None = None,
) -> AdminCourseListResponse:
    total, courses = await course_crud.list_all_courses(db, page, page_size, status, keyword)
    items = []
    for c in courses:
        item = CourseRead.model_validate(c)
        if c.teacher:
            item.teacher_name = c.teacher.name
        items.append(item)
    return AdminCourseListResponse(total=total, items=items)


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def admin_create_course(
    course_in: AdminCourseCreate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseRead:
    # Verify teacher exists
    teacher = await db.get(Teacher, course_in.teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="讲师不存在")
    data = course_in.model_dump()
    teacher_id = data.pop("teacher_id")
    course = Course(teacher_id=teacher_id, **data)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return CourseRead.model_validate(course)


@router.put("/courses/{course_id}", response_model=CourseRead)
async def admin_update_course(
    course_id: int,
    payload: dict[str, Any],
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseRead:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    allowed = {"title", "description", "cover", "category", "total_hours", "teacher_id", "status", "rating"}
    for key, value in payload.items():
        if key not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知字段：{key}")
        if key == "teacher_id":
            teacher = await db.get(Teacher, value)
            if teacher is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="讲师不存在")
        setattr(course, key, value)
    await db.commit()
    await db.refresh(course)
    return CourseRead.model_validate(course)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_course(
    course_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    await course_crud.delete_course_soft(db, course)


# ── Admin Review Management ──

@router.get("/reviews", response_model=AdminReviewListResponse)
async def admin_list_reviews(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    course_id: int | None = None,
) -> AdminReviewListResponse:
    from app.crud.review_crud import list_all_reviews

    total, reviews = await list_all_reviews(db, page, page_size, course_id)
    items = []
    for r in reviews:
        items.append(
            AdminReviewOut(
                id=r.id,
                course_id=r.course_id,
                course_title=r.course.title if r.course else "",
                user_id=r.user_id,
                username=r.user.username if r.user else "",
                rating=r.rating,
                content=r.content,
                created_at=r.created_at,
            )
        )
    return AdminReviewListResponse(total=total, items=items)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_review(
    review_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    from app.crud.review_crud import delete_review

    review = await db.get(CourseReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评价不存在")
    await delete_review(db, review)
    await db.commit()


# ── Admin Teacher List (for course creation dropdown) ──

@router.get("/teachers")
async def admin_list_teachers(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, int | str]]:
    """List all approved teachers with name and id for admin UI dropdowns."""
    result = await db.execute(
        select(Teacher).where(Teacher.status == TeacherStatus.approved)
    )
    teachers = result.scalars().all()
    return [{"id": t.id, "name": t.name} for t in teachers]


# ── Admin User Account Deletion ──


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    try:
        await user_crud.hard_delete_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Admin Order Management ──


@router.get("/orders", response_model=OrderListResponse)
async def admin_list_orders(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    order_sn: str | None = None,
) -> OrderListResponse:
    stmt = select(Order)
    if status_filter is not None:
        stmt = stmt.where(Order.status == status_filter)
    if order_sn:
        stmt = stmt.where(Order.order_sn.like(f"%{order_sn}%"))
    total_result = await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    total = total_result.scalar_one()
    result = await db.execute(
        stmt.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(Order.items).selectinload(OrderItem.sku).selectinload(CourseSKU.course), selectinload(Order.user))
    )
    orders = list(result.scalars().all())
    return OrderListResponse(
        total=total,
        items=[
            OrderOut(
                id=o.id,
                order_sn=o.order_sn,
                total_amount=o.total_amount,
                pay_amount=o.pay_amount,
                status=o.status,
                user_id=o.user_id,
                username=o.user.username if o.user else None,
                expire_time=o.expire_time,
                pay_time=o.pay_time,
                created_at=o.created_at,
                items=[
                    OrderItemOut(
                        id=i.id,
                        sku_id=i.sku_id,
                        quantity=i.quantity,
                        price=i.price,
                        course_title=i.sku.course.title if i.sku and i.sku.course else None,
                        sku_name=i.sku.sku_name if i.sku else None,
                    )
                    for i in o.items
                ],
            )
            for o in orders
        ],
    )


@router.post("/orders/{order_sn}/refund")
async def admin_refund_order(
    order_sn: str,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    """Admin refund: restore stock, cancel order, and remove course access."""
    result = await db.execute(
        select(Order)
        .where(Order.order_sn == order_sn)
        .with_for_update()
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order.status not in {OrderStatus.paid, OrderStatus.learning}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有已支付订单才能退款")

    # Restore SKU stock
    sku_ids = [item.sku_id for item in order.items]
    sku_result = await db.execute(select(CourseSKU).where(CourseSKU.id.in_(sku_ids)).with_for_update())
    sku_map = {sku.id: sku for sku in sku_result.scalars().all()}
    for item in order.items:
        if item.sku_id in sku_map:
            sku_map[item.sku_id].stock += item.quantity

    # Remove course access (UserCourse)
    from app.models import UserCourse
    for item in order.items:
        await db.execute(
            delete(UserCourse).where(
                UserCourse.user_id == order.user_id,
                UserCourse.sku_id == item.sku_id,
            )
        )

    order.status = OrderStatus.cancelled
    await db.commit()
    return {"status": "refunded", "order_sn": order_sn}
