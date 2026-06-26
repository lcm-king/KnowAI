import asyncio
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
from app.crud.user_course_crud import grant_courses_for_order
from app.database import AsyncSessionLocal, get_db
from app.models import CourseSKU, CourseStatus, Order, OrderItem, OrderStatus, User
from app.schemas import PayCreateRequest, PayCreateResponse, PayNotifyRequest, PayStatusResponse
from app.services.alipay import create_alipay_order, query_alipay_trade, verify_alipay_notify
from app.services.wechat_pay import create_wechat_order, verify_wechat_notify

router = APIRouter()


async def get_order_for_pay(db: AsyncSession, user_id: int, order_sn: str) -> Order:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.order_sn == order_sn)
        .options(
            selectinload(Order.items)
            .selectinload(OrderItem.sku)
            .selectinload(CourseSKU.course)
        )
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单不可支付")
    if order.expire_time <= datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单已过期")
    # Verify all courses in the order are still published
    for item in order.items:
        if item.sku is None or item.sku.course is None or item.sku.course.status != CourseStatus.published:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="课程不存在或已下架")
    return order


async def mark_order_paid(order_sn: str) -> bool:
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                select(Order)
                .where(Order.order_sn == order_sn)
                .with_for_update()
                .options(selectinload(Order.items).selectinload(OrderItem.sku).selectinload(CourseSKU.course))
            )
            order = result.scalar_one_or_none()
            if order is None:
                return False
            if order.status != OrderStatus.pending:
                return order.status in {OrderStatus.paid, OrderStatus.learning}
            order.status = OrderStatus.paid
            order.pay_time = datetime.now()
            await grant_courses_for_order(db, order)
        return True


async def simulate_pay_success(order_sn: str) -> None:
    await asyncio.sleep(5)
    paid = await mark_order_paid(order_sn)
    if paid:
        print(f"Mock payment success for order {order_sn}")


_poll_tasks: set[asyncio.Task] = set()


async def poll_alipay_trade(order_sn: str) -> None:
    """Poll Alipay trade status until paid or timeout (5 min)."""
    loop = asyncio.get_running_loop()
    logger.info("Starting Alipay trade polling for order %s", order_sn)
    for i in range(60):
        await asyncio.sleep(5)
        try:
            status = await loop.run_in_executor(None, query_alipay_trade, order_sn)
            logger.info("Alipay poll [%d/60] order=%s status=%r", i + 1, order_sn, status)
            if status == "TRADE_SUCCESS":
                paid = await mark_order_paid(order_sn)
                if paid:
                    logger.info("Alipay trade paid successfully: %s", order_sn)
                return
        except Exception as e:
            logger.error("Alipay poll error for %s: %s", order_sn, e, exc_info=True)
    logger.warning("Alipay polling timed out for order %s", order_sn)


@router.post("/create", response_model=PayCreateResponse)
async def create_pay_order(
    payload: PayCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayCreateResponse:
    order = await get_order_for_pay(db, current_user.id, payload.order_sn)
    if payload.pay_method == "wechat":
        pay_data = await create_wechat_order(order.order_sn, order.pay_amount)
    else:
        pay_data = await create_alipay_order(order.order_sn, order.pay_amount)
        if settings.alipay_sandbox:
            task = asyncio.create_task(poll_alipay_trade(order.order_sn))
            _poll_tasks.add(task)
            task.add_done_callback(_poll_tasks.discard)

    # Mock payment: auto-complete after a short delay
    if pay_data.get("mock", settings.pay_mock):
        task = asyncio.create_task(simulate_pay_success(order.order_sn))
        _poll_tasks.add(task)
        task.add_done_callback(_poll_tasks.discard)

    return PayCreateResponse(
        order_sn=order.order_sn,
        pay_method=payload.pay_method,
        pay_url=pay_data.get("pay_url"),
        qr_code_url=pay_data.get("qr_code_url"),
        form=pay_data.get("form"),
        mock=bool(pay_data.get("mock", settings.pay_mock)),
    )


@router.post("/notify")
async def pay_notify(payload: PayNotifyRequest) -> dict[str, str]:
    data = payload.model_dump()
    if payload.pay_method == "wechat" and not verify_wechat_notify(data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效签名")
    if payload.pay_method == "alipay" and not verify_alipay_notify(data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效签名")
    if payload.status != "success":
        return {"message": "ignored"}

    paid = await mark_order_paid(payload.order_sn)
    if not paid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return {"message": "success"}


@router.post("/notify/alipay")
async def alipay_form_notify(request: Request) -> str:
    """Handle form-encoded POST from real Alipay async notification."""
    form_data = await request.form()
    data = dict(form_data)

    if not verify_alipay_notify(data):
        logger.error("Alipay notify signature verification failed")
        return "failure"

    trade_status = data.get("trade_status", "")
    if trade_status != "TRADE_SUCCESS":
        logger.info(f"Ignored Alipay notify with trade_status={trade_status}")
        return "success"

    order_sn = data.get("out_trade_no", "")
    if not order_sn:
        logger.error("Alipay notify missing out_trade_no")
        return "failure"

    paid = await mark_order_paid(order_sn)
    if not paid:
        logger.error(f"Order {order_sn} not found or already paid")
        return "failure"

    return "success"


@router.get("/status/{order_sn}", response_model=PayStatusResponse)
async def pay_status(
    order_sn: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayStatusResponse:
    result = await db.execute(select(Order).where(Order.user_id == current_user.id, Order.order_sn == order_sn))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return PayStatusResponse(order_sn=order.order_sn, status=order.status, paid=order.status in {OrderStatus.paid, OrderStatus.learning})
