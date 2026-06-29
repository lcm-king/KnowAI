from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserRole(StrEnum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class TeacherStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CourseStatus(StrEnum):
    draft = "draft"
    pending = "pending"
    published = "published"
    closed = "closed"


class SKUStatus(StrEnum):
    on = "on"
    off = "off"


class OrderStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    learning = "learning"
    completed = "completed"
    cancelled = "cancelled"
    refunding = "refunding"


class SeckillStatus(StrEnum):
    pending = "pending"
    active = "active"
    finished = "finished"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    teacher_profile: Mapped[Teacher | None] = relationship(
        foreign_keys=[teacher_id],
        post_update=True,
    )
    orders: Mapped[list[Order]] = relationship(back_populates="user")
    courses_owned: Mapped[list[UserCourse]] = relationship(back_populates="user")
    favorites: Mapped[list[Favorite]] = relationship(back_populates="user")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TeacherStatus] = mapped_column(Enum(TeacherStatus), default=TeacherStatus.pending, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    courses: Mapped[list[Course]] = relationship(back_populates="teacher")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    total_hours: Mapped[float] = mapped_column(Float, default=0)
    learn_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[CourseStatus] = mapped_column(Enum(CourseStatus), default=CourseStatus.draft, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    teacher: Mapped[Teacher] = relationship(back_populates="courses")
    skus: Mapped[list[CourseSKU]] = relationship(back_populates="course")
    favorites: Mapped[list[Favorite]] = relationship(back_populates="course")
    chapters: Mapped[list[Chapter]] = relationship(back_populates="course", order_by="Chapter.sort_order")
    reviews: Mapped[list[CourseReview]] = relationship(back_populates="course", cascade="all, delete-orphan")
    knowledge_files: Mapped[list[CourseKnowledge]] = relationship(back_populates="course", cascade="all, delete-orphan")


class CourseSKU(Base):
    __tablename__ = "course_skus"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    sku_name: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    validity_days: Mapped[int] = mapped_column(Integer, default=365)
    status: Mapped[SKUStatus] = mapped_column(Enum(SKUStatus), default=SKUStatus.on, nullable=False)

    course: Mapped[Course] = relationship(back_populates="skus")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="sku")
    user_courses: Mapped[list[UserCourse]] = relationship(back_populates="sku")
    seckill_activities: Mapped[list[SeckillActivity]] = relationship(back_populates="sku")


class SeckillActivity(Base):
    __tablename__ = "seckill_activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("course_skus.id"), nullable=False)
    seckill_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    limit_quantity: Mapped[int] = mapped_column(Integer, default=1)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[SeckillStatus] = mapped_column(Enum(SeckillStatus), default=SeckillStatus.pending, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sku: Mapped[CourseSKU] = relationship(back_populates="seckill_activities")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_sn: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    pay_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seckill_activity_id: Mapped[int | None] = mapped_column(ForeignKey("seckill_activities.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("course_skus.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    sku: Mapped[CourseSKU] = relationship(back_populates="order_items")


class UserCourse(Base):
    __tablename__ = "user_courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("course_skus.id"), nullable=False)
    expire_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="courses_owned")
    course: Mapped[Course] = relationship()
    sku: Mapped[CourseSKU] = relationship(back_populates="user_courses")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship()
    course: Mapped[Course] = relationship()


class SystemConfig(Base):
    """系统配置键值对。"""
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    course: Mapped[Course] = relationship(back_populates="chapters")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="chapter", order_by="Lesson.sort_order")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="lessons")
    knowledge_files: Mapped[list[LessonKnowledge]] = relationship(back_populates="lesson", cascade="all, delete-orphan")


class LessonKnowledge(Base):
    __tablename__ = "lesson_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lesson: Mapped[Lesson] = relationship(back_populates="knowledge_files")


class CourseKnowledge(Base):
    __tablename__ = "course_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    course: Mapped[Course] = relationship(back_populates="knowledge_files")


class KnowledgeVector(Base):
    """向量索引元数据：追踪每个课程/课时的向量索引状态。"""
    __tablename__ = "knowledge_vectors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    file_id: Mapped[int] = mapped_column(nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "course" or "lesson"
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_store_id: Mapped[str] = mapped_column(String(100), nullable=False)  # Chroma collection name
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CourseReview(Base):
    """课程评价/评分。"""
    __tablename__ = "course_reviews"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_user_review"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    course: Mapped[Course] = relationship(back_populates="reviews")
    user: Mapped[User] = relationship()


class CourseQuestion(Base):
    """课程问答-问题。"""
    __tablename__ = "course_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    answers: Mapped[list["CourseAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class CourseAnswer(Base):
    """课程问答-回答。"""
    __tablename__ = "course_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("course_questions.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_teacher_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    question: Mapped[CourseQuestion] = relationship(back_populates="answers")
