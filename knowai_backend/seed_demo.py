import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.database import AsyncSessionLocal, get_redis, init_db, init_redis
from app.models import Course, CourseSKU, CourseStatus, Order, OrderItem, OrderStatus, SeckillActivity, SeckillStatus, SKUStatus, Teacher, TeacherStatus, User, UserRole


async def get_or_create_user(db: AsyncSession, username: str, phone: str, email: str, role: UserRole) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is not None:
        user.phone = phone
        user.email = email
        user.role = role
        user.is_active = True
        return user
    user = User(
        username=username,
        phone=phone,
        email=email,
        password_hash=get_password_hash("123456"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_or_create_teacher(db: AsyncSession, user: User) -> Teacher:
    result = await db.execute(select(Teacher).where(Teacher.user_id == user.id))
    teacher = result.scalar_one_or_none()
    if teacher is not None:
        return teacher
    teacher = Teacher(
        user_id=user.id,
        name="KnowAI 教研中心",
        bio="专注 AI、Python 与数据分析课程研发。",
        avatar="https://dummyimage.com/200x200/7c3aed/ffffff&text=AI",
        status=TeacherStatus.approved,
    )
    db.add(teacher)
    await db.flush()
    user.teacher_id = teacher.id
    return teacher


async def create_course_if_missing(
    db: AsyncSession,
    teacher_id: int,
    title: str,
    description: str,
    category: str,
    total_hours: int,
    price: str,
    stock: int,
    cover: str,
) -> Course:
    result = await db.execute(select(Course).where(Course.title == title))
    existing_course = result.scalar_one_or_none()
    if existing_course is not None:
        return existing_course
    course = Course(
        teacher_id=teacher_id,
        title=title,
        description=description,
        cover=cover,
        category=category,
        total_hours=total_hours,
        learn_count=128,
        rating=4.8,
        status=CourseStatus.published,
    )
    db.add(course)
    await db.flush()
    db.add(
        CourseSKU(
            course_id=course.id,
            sku_name="标准版",
            price=Decimal(price),
            stock=stock,
            validity_days=365,
            status=SKUStatus.on,
        )
    )
    return course


async def create_demo_seckill(db: AsyncSession, course: Course) -> None:
    result = await db.execute(select(CourseSKU).where(CourseSKU.course_id == course.id, CourseSKU.status == SKUStatus.on))
    sku = result.scalars().first()
    if sku is None:
        return
    activity_result = await db.execute(select(SeckillActivity).where(SeckillActivity.sku_id == sku.id))
    activity = activity_result.scalar_one_or_none()
    if activity is None:
        activity = SeckillActivity(
            sku_id=sku.id,
            seckill_price=Decimal("9.90"),
            stock=20,
            limit_quantity=1,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now() + timedelta(days=7),
            status=SeckillStatus.active,
        )
        db.add(activity)
        await db.flush()
    else:
        activity.status = SeckillStatus.active
        activity.start_time = datetime.now() - timedelta(hours=1)
        activity.end_time = datetime.now() + timedelta(days=7)
        activity.stock = max(activity.stock, 20)
    redis = await get_redis()
    await redis.set(f"seckill:stock:{activity.id}", activity.stock)


async def seed() -> None:
    await init_db()
    await init_redis()
    async with AsyncSessionLocal() as db:
        teacher_user = await get_or_create_user(db, "teacher", "18800000001", "teacher@example.com", UserRole.teacher)
        student_user = await get_or_create_user(db, "student", "18800000002", "student@example.com", UserRole.student)
        await get_or_create_user(db, "admin", "18800000003", "admin@example.com", UserRole.admin)
        teacher = await get_or_create_teacher(db, teacher_user)
        courses = [
            (
                "AI 大模型应用实战",
                "从提示词工程到企业知识库，完整掌握大模型应用落地流程。",
                "AI",
                32,
                "199.00",
                100,
                "https://dummyimage.com/600x360/2563eb/ffffff&text=AI+LLM",
            ),
            (
                "Python 数据分析入门",
                "使用 NumPy、Pandas 和可视化工具完成真实数据分析项目。",
                "Python",
                24,
                "129.00",
                120,
                "https://dummyimage.com/600x360/16a34a/ffffff&text=Python",
            ),
            (
                "机器学习项目课",
                "覆盖特征工程、模型训练、评估调优和上线部署。",
                "AI",
                40,
                "249.00",
                80,
                "https://dummyimage.com/600x360/9333ea/ffffff&text=ML",
            ),
            (
                "前端工程化与 Vue3",
                "基于 Vue3、Vite 和 TypeScript 构建现代化前端项目。",
                "前端",
                28,
                "159.00",
                90,
                "https://dummyimage.com/600x360/0f766e/ffffff&text=Vue3",
            ),
            (
                "编程基础：Python 入门",
                "零基础也能学会的 Python 编程课，从变量到函数，带你入门编程世界。",
                "编程",
                20,
                "0.00",
                999,
                "",
            ),
            (
                "AI 时代必备指南",
                "了解人工智能基本概念、发展历程与未来趋势，人人可学的 AI 科普课。",
                "AI",
                12,
                "0.00",
                999,
                "",
            ),
            (
                "高效学习法",
                "掌握科学的学习方法和记忆技巧，让学习效率翻倍。",
                "综合",
                8,
                "0.00",
                999,
                "",
            ),
        ]
        seeded_courses = []
        for course in courses:
            seeded_courses.append(await create_course_if_missing(db, teacher.id, *course))
        await create_demo_seckill(db, seeded_courses[0])
        await db.commit()

        # ---------- 创建演示订单（让讲师看板有真实销量数据） ----------
        existing_order = await db.execute(
            select(Order).where(Order.user_id == student_user.id).limit(1)
        )
        if existing_order.scalar_one_or_none() is None:
            now = datetime.now()
            order = Order(
                user_id=student_user.id,
                order_sn=f"DEMO{now.strftime('%Y%m%d%H%M%S%f')}",
                total_amount=Decimal("0.00"),
                pay_amount=Decimal("577.00"),
                status=OrderStatus.paid,
                pay_time=now,
                expire_time=now + timedelta(hours=1),
            )
            db.add(order)
            await db.flush()

            # 为每门付费课程创建订单条目（不同数量模拟真实销量差异）
            sku_result = await db.execute(
                select(CourseSKU).where(
                    CourseSKU.course_id.in_([c.id for c in seeded_courses]),
                    CourseSKU.sku_name == "标准版",
                )
            )
            skus = sku_result.scalars().all()
            for sku in skus:
                qty = 1
                db.add(OrderItem(order_id=order.id, sku_id=sku.id, quantity=qty, price=sku.price))
                sku.stock = max(sku.stock - qty, 0)
            await db.commit()
            print(f"演示订单已创建: {order.order_sn}")


if __name__ == "__main__":
    asyncio.run(seed())
