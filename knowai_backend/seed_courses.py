"""一次性造数脚本：创建多个讲师 + 计算机课程（免费试看 + 付费完整版 + 秒杀活动）。"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal, init_db
from app.models import (
    Course,
    CourseSKU,
    CourseStatus,
    Order,
    OrderItem,
    OrderStatus,
    SeckillActivity,
    SeckillStatus,
    SKUStatus,
    Teacher,
    TeacherStatus,
    User,
    UserRole,
)
from app.tasks.sync_es import sync_course_to_es


NEW_TEACHERS = [
    {
        "username": "teacher_wang",
        "phone": "13900000001",
        "email": "wang@knowai.local",
        "password": "teacher123",
        "name": "王老师",
        "bio": "AI 算法工程师，10 年深度学习经验，专注 NLP 与计算机视觉。",
    },
    {
        "username": "teacher_li",
        "phone": "13900000002",
        "email": "li@knowai.local",
        "password": "teacher123",
        "name": "李老师",
        "bio": "全栈架构师，前大厂技术专家，专注前端工程化与云原生。",
    },
    {
        "username": "teacher_zhang",
        "phone": "13900000003",
        "email": "zhang@knowai.local",
        "password": "teacher123",
        "name": "张老师",
        "bio": "985 高校计算机系副教授，主讲数据结构、操作系统、编译原理等核心课程。",
    },
    {
        "username": "teacher_chen",
        "phone": "13900000004",
        "email": "chen@knowai.local",
        "password": "teacher123",
        "name": "陈老师",
        "bio": "数据科学家，专注 Python 数据栈、机器学习与商业智能落地。",
    },
    {
        "username": "teacher_liu",
        "phone": "13900000005",
        "email": "liu@knowai.local",
        "password": "teacher123",
        "name": "刘老师",
        "bio": "资深安全工程师，长期从事渗透测试、密码学与零信任架构研究。",
    },
    {
        "username": "teacher_zhao",
        "phone": "13900000006",
        "email": "zhao@knowai.local",
        "password": "teacher123",
        "name": "赵老师",
        "bio": "Java 技术专家，专注高并发、分布式架构与中间件源码。",
    },
]


COURSES_DATA = {
    "teacher_wang": [
        {
            "title": "深度学习 PyTorch 实战",
            "category": "AI",
            "description": "从零搭建 CNN、RNN、Transformer，覆盖图像分类、文本生成、模型部署全流程。",
            "total_hours": 48,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("399.00"), "stock": 100, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("99.00"), "stock": 50},
        },
        {
            "title": "NLP 自然语言处理详解",
            "category": "AI",
            "description": "分词、词向量、BERT、GPT 原理与微调实战，附完整项目代码。",
            "total_hours": 36,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("299.00"), "stock": 80, "validity_days": 365},
            ],
        },
        {
            "title": "计算机视觉基础",
            "category": "AI",
            "description": "图像处理、目标检测、人脸识别经典算法与工程落地。",
            "total_hours": 32,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("259.00"), "stock": 120, "validity_days": 365},
            ],
        },
    ],
    "teacher_li": [
        {
            "title": "React 18 进阶与源码剖析",
            "category": "前端",
            "description": "并发渲染、Suspense、Server Components 原理剖析，手写 mini-react。",
            "total_hours": 40,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("329.00"), "stock": 90, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("79.00"), "stock": 60},
        },
        {
            "title": "Node.js 后端开发实战",
            "category": "后端",
            "description": "Express、Koa、Nest.js 对比实践，PM2 部署、性能调优一应俱全。",
            "total_hours": 28,
            "rating": 4.6,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("199.00"), "stock": 150, "validity_days": 365},
            ],
        },
        {
            "title": "Go 语言入门到精通",
            "category": "后端",
            "description": "语法基础、并发编程、gRPC、微服务架构，适合后端工程师转型。",
            "total_hours": 44,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("349.00"), "stock": 110, "validity_days": 365},
            ],
        },
        {
            "title": "Docker 与 Kubernetes 实战",
            "category": "运维",
            "description": "容器化、集群部署、CI/CD 流水线，云原生工程师必修课。",
            "total_hours": 52,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("399.00"), "stock": 70, "validity_days": 365},
            ],
        },
    ],
    "teacher_zhang": [
        {
            "title": "数据结构与算法精讲",
            "category": "计算机基础",
            "description": "数组、链表、树、图、动态规划、贪心算法，配套 LeetCode 高频题精解。",
            "total_hours": 56,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("359.00"), "stock": 200, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("89.00"), "stock": 80},
        },
        {
            "title": "操作系统原理与实践",
            "category": "计算机基础",
            "description": "进程与线程、内存管理、文件系统、调度算法，配合 Linux 内核源码剖析。",
            "total_hours": 60,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("399.00"), "stock": 150, "validity_days": 365},
            ],
        },
        {
            "title": "计算机网络：从原理到实战",
            "category": "计算机基础",
            "description": "TCP/IP、HTTP/2/3、WebSocket、CDN 原理，抓包分析与性能优化全流程。",
            "total_hours": 44,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("329.00"), "stock": 180, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("69.00"), "stock": 100},
        },
        {
            "title": "数据库系统概论",
            "category": "计算机基础",
            "description": "关系代数、SQL 优化、事务隔离、索引设计，MySQL / PostgreSQL 对比实战。",
            "total_hours": 40,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("299.00"), "stock": 220, "validity_days": 365},
            ],
        },
        {
            "title": "编译原理",
            "category": "计算机基础",
            "description": "词法分析、语法分析、语义分析、中间代码生成，手写一门 Mini 语言编译器。",
            "total_hours": 48,
            "rating": 4.6,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("349.00"), "stock": 90, "validity_days": 365},
            ],
        },
        {
            "title": "计算机组成原理",
            "category": "计算机基础",
            "description": "指令集、流水线、Cache、虚拟内存，从晶体管到 CPU 的完整链路。",
            "total_hours": 36,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("269.00"), "stock": 120, "validity_days": 365},
            ],
        },
        {
            "title": "软件工程与项目管理",
            "category": "计算机基础",
            "description": "需求分析、UML 建模、敏捷开发、CI/CD、代码评审，工程师进阶必读。",
            "total_hours": 32,
            "rating": 4.5,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("239.00"), "stock": 160, "validity_days": 365},
            ],
        },
    ],
    "teacher_chen": [
        {
            "title": "Python 数据分析与可视化",
            "category": "数据科学",
            "description": "NumPy、Pandas、Matplotlib、Seaborn 全流程，电商用户行为分析实战。",
            "total_hours": 36,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("259.00"), "stock": 200, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("59.00"), "stock": 120},
        },
        {
            "title": "机器学习入门到进阶",
            "category": "AI",
            "description": "线性回归、决策树、SVM、集成学习、聚类，scikit-learn 实战项目全解。",
            "total_hours": 50,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("379.00"), "stock": 130, "validity_days": 365},
            ],
        },
        {
            "title": "大数据 Spark 实战",
            "category": "数据科学",
            "description": "RDD、DataFrame、Spark SQL、Streaming、MLlib，PB 级数据处理最佳实践。",
            "total_hours": 42,
            "rating": 4.6,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("329.00"), "stock": 100, "validity_days": 365},
            ],
        },
        {
            "title": "SQL 数据查询与优化",
            "category": "数据科学",
            "description": "窗口函数、CTE、执行计划、索引调优，从入门到 DBA 视角的实战手册。",
            "total_hours": 28,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("199.00"), "stock": 240, "validity_days": 365},
            ],
        },
    ],
    "teacher_liu": [
        {
            "title": "网络安全攻防实战",
            "category": "安全",
            "description": "Web 漏洞、内网渗透、提权、应急响应，红蓝对抗全流程复盘。",
            "total_hours": 46,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("399.00"), "stock": 80, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("99.00"), "stock": 60},
        },
        {
            "title": "密码学基础与应用",
            "category": "安全",
            "description": "对称 / 非对称加密、哈希、数字签名、PKI，TLS 1.3 协议深度剖析。",
            "total_hours": 32,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("259.00"), "stock": 100, "validity_days": 365},
            ],
        },
        {
            "title": "零信任架构与企业安全",
            "category": "安全",
            "description": "身份治理、最小权限、微隔离、SASE，现代企业安全体系建设指南。",
            "total_hours": 26,
            "rating": 4.6,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("229.00"), "stock": 90, "validity_days": 365},
            ],
        },
    ],
    "teacher_zhao": [
        {
            "title": "Java 并发编程实战",
            "category": "后端",
            "description": "JMM、锁、AQS、线程池、并发容器、虚拟线程，深入 JDK 源码剖析。",
            "total_hours": 44,
            "rating": 4.9,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("359.00"), "stock": 150, "validity_days": 365},
            ],
            "seckill": {"seckill_price": Decimal("89.00"), "stock": 80},
        },
        {
            "title": "Spring Cloud 微服务架构",
            "category": "后端",
            "description": "注册中心、配置中心、网关、熔断、链路追踪，搭建生产级微服务体系。",
            "total_hours": 48,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("379.00"), "stock": 110, "validity_days": 365},
            ],
        },
        {
            "title": "Redis 深度历险",
            "category": "后端",
            "description": "数据结构、持久化、主从、Cluster、缓存三大问题与高可用架构设计。",
            "total_hours": 30,
            "rating": 4.8,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("239.00"), "stock": 180, "validity_days": 365},
            ],
        },
        {
            "title": "分布式系统设计",
            "category": "后端",
            "description": "CAP、一致性算法、分布式事务、消息队列、幂等设计，从理论到落地。",
            "total_hours": 40,
            "rating": 4.7,
            "skus": [
                {"sku_name": "免费试看版", "price": Decimal("0.00"), "stock": 999, "validity_days": 7},
                {"sku_name": "完整版", "price": Decimal("329.00"), "stock": 130, "validity_days": 365},
            ],
        },
    ],
}


async def get_or_create_teacher(db, info: dict) -> Teacher:
    result = await db.execute(select(Teacher).where(Teacher.name == info["name"]))
    teacher = result.scalar_one_or_none()
    if teacher is not None:
        return teacher

    user = User(
        username=info["username"],
        phone=info["phone"],
        email=info["email"],
        password_hash=get_password_hash(info["password"]),
        role=UserRole.teacher,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    teacher = Teacher(
        user_id=user.id,
        name=info["name"],
        bio=info["bio"],
        status=TeacherStatus.approved,
    )
    db.add(teacher)
    await db.flush()
    return teacher


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        teacher_map: dict[str, Teacher] = {}
        for info in NEW_TEACHERS:
            teacher = await get_or_create_teacher(db, info)
            teacher_map[info["username"]] = teacher
            print(f"讲师就绪: {teacher.name} (id={teacher.id}, user_id={teacher.user_id})")

        now = datetime.now()
        all_full_skus: list[CourseSKU] = []
        for teacher_username, courses in COURSES_DATA.items():
            teacher = teacher_map[teacher_username]
            for cdata in courses:
                result = await db.execute(
                    select(Course).where(Course.title == cdata["title"], Course.teacher_id == teacher.id)
                )
                existing = result.scalar_one_or_none()
                if existing is not None:
                    print(f"  跳过已存在课程: {cdata['title']}")
                    continue

                course = Course(
                    teacher_id=teacher.id,
                    title=cdata["title"],
                    description=cdata["description"],
                    category=cdata["category"],
                    total_hours=cdata["total_hours"],
                    rating=cdata["rating"],
                    learn_count=0,
                    status=CourseStatus.published,
                )
                db.add(course)
                await db.flush()
                course_id = course.id

                full_sku_id: int | None = None
                for sku_data in cdata["skus"]:
                    sku = CourseSKU(
                        course_id=course_id,
                        sku_name=sku_data["sku_name"],
                        price=sku_data["price"],
                        stock=sku_data["stock"],
                        validity_days=sku_data["validity_days"],
                        status=SKUStatus.on,
                    )
                    db.add(sku)
                    await db.flush()
                    if sku_data["sku_name"] == "完整版":
                        full_sku_id = sku.id
                        all_full_skus.append(sku)

                if "seckill" in cdata and full_sku_id is not None:
                    sq = cdata["seckill"]
                    activity = SeckillActivity(
                        sku_id=full_sku_id,
                        seckill_price=sq["seckill_price"],
                        stock=sq["stock"],
                        limit_quantity=1,
                        start_time=now - timedelta(minutes=10),
                        end_time=now + timedelta(days=7),
                        status=SeckillStatus.active,
                    )
                    db.add(activity)
                    await db.flush()
                    seckill_info = f" + 秒杀活动(id={activity.id} 抢购价={activity.seckill_price})"
                else:
                    seckill_info = ""

                await db.commit()
                await sync_course_to_es(course_id)
                print(f"  创建课程: {cdata['title']} (id={course_id}, teacher={teacher.name}){seckill_info}")

        # ---------- 创建演示订单，让讲师看板有销量数据 ----------
        student_user = await db.execute(select(User).where(User.username == "demo_student"))
        student = student_user.scalar_one_or_none()
        if student is None:
            student = User(
                username="demo_student",
                phone="18800000002",
                email="student@knowai.local",
                password_hash=get_password_hash("123456"),
                role=UserRole.student,
                is_active=True,
            )
            db.add(student)
            await db.flush()

        if all_full_skus:
            # 检查这些 SKU 是否已有订单
            existing_item = await db.execute(
                select(OrderItem).where(OrderItem.sku_id.in_([s.id for s in all_full_skus])).limit(1)
            )
            if existing_item.scalar_one_or_none() is None:
                order_sn = f"DEMO{now.strftime('%Y%m%d%H%M%S%f')}"
                pay_amount = sum((s.price for s in all_full_skus[:5]), Decimal("0.00"))
                order = Order(
                    user_id=student.id,
                    order_sn=order_sn,
                    total_amount=Decimal("0.00"),
                    pay_amount=pay_amount,
                    status=OrderStatus.paid,
                    pay_time=now,
                    expire_time=now + timedelta(hours=1),
                )
                db.add(order)
                await db.flush()

                for sku in all_full_skus[:5]:
                    db.add(OrderItem(order_id=order.id, sku_id=sku.id, quantity=1, price=sku.price))
                    sku.stock = max(sku.stock - 1, 0)
                await db.commit()
                print(f"演示订单已创建(order={order_sn})，包含 {min(5, len(all_full_skus))} 门课程（属于 {len(set(s.course_id for s in all_full_skus[:5]))} 位讲师）")


if __name__ == "__main__":
    asyncio.run(seed())
