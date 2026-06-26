from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import CourseStatus, OrderStatus, SKUStatus, SeckillStatus, TeacherStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    jti: str


class SendCodeRequest(BaseModel):
    target: str = Field(min_length=5, max_length=100)


class TeacherBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    bio: str | None = None
    avatar: str | None = None


class TeacherCreate(TeacherBase):
    user_id: int


class TeacherRead(TeacherBase):
    id: int
    user_id: int
    status: TeacherStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseTeacherRead(BaseModel):
    id: int
    name: str
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    code: str = Field(min_length=4, max_length=4)


class RegisterResponse(BaseModel):
    message: str = "注册成功，请登录"


class PhoneCodeLogin(BaseModel):
    phone: str = Field(min_length=5, max_length=20)
    code: str = Field(min_length=4, max_length=4)


class ApplyTeacherRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    bio: str | None = None


class UserRead(UserBase):
    id: int
    role: UserRole
    teacher_id: int | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    account: str = Field(min_length=3, max_length=100)
    password: str


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    cover: str | None = None
    video_url: str | None = None
    category: str | None = Field(default=None, max_length=50)
    total_hours: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    cover: str | None = None
    video_url: str | None = None
    category: str | None = Field(default=None, max_length=50)
    total_hours: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)


class CourseSKUCreate(BaseModel):
    sku_name: str | None = Field(default=None, max_length=100)
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    stock: int = Field(default=0, ge=0)
    validity_days: int = Field(default=365, ge=1)


class CourseSKUUpdate(BaseModel):
    sku_name: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    validity_days: int | None = Field(default=None, ge=1)
    status: SKUStatus | None = None


class CourseSKURead(BaseModel):
    id: int
    course_id: int
    sku_name: str | None = None
    price: Decimal
    stock: int
    validity_days: int
    status: SKUStatus

    model_config = ConfigDict(from_attributes=True)


class CourseRead(BaseModel):
    id: int
    teacher_id: int
    teacher_name: str | None = None
    title: str
    description: str | None = None
    cover: str | None = None
    video_url: str | None = None
    category: str | None = None
    total_hours: int
    learn_count: int
    rating: float
    status: CourseStatus
    created_at: datetime
    updated_at: datetime | None = None
    price: Decimal | None = None
    stock: int | None = None
    validity_days: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CourseDetailRead(CourseRead):
    teacher: CourseTeacherRead
    skus: list[CourseSKURead] = []
    seckill_activity_id: int | None = None
    seckill_price: Decimal | None = None
    seckill_end_time: datetime | None = None
    is_purchased: bool = False


class CourseListResponse(BaseModel):
    total: int
    items: list[CourseRead]


class CourseDetailListResponse(BaseModel):
    total: int
    items: list[CourseDetailRead]


class SalesStatistics(BaseModel):
    total_sales: Decimal
    order_count: int
    hot_courses: list[dict[str, int | str]]


class CartAddRequest(BaseModel):
    sku_id: int
    quantity: int = Field(default=1, ge=1, le=1)


class CartUpdateRequest(BaseModel):
    sku_id: int
    quantity: int | None = Field(default=None, ge=1, le=1)
    selected: bool | None = None


class CartRemoveRequest(BaseModel):
    sku_id: int


class CartMergeItem(BaseModel):
    sku_id: int
    quantity: int = Field(default=1, ge=1, le=1)
    selected: bool = True
    add_time: int | None = None


class CartMergeRequest(BaseModel):
    items: list[CartMergeItem]


class CartItemRead(BaseModel):
    sku_id: int
    course_id: int
    course_title: str
    cover: str | None = None
    sku_name: str | None = None
    price: Decimal
    quantity: int
    selected: bool
    add_time: int


class CartRead(BaseModel):
    total: int
    items: list[CartItemRead]


class OrderCreate(BaseModel):
    sku_ids: list[int] = Field(min_length=1)
    address_id: int | None = None


class OrderItemOut(BaseModel):
    id: int
    sku_id: int
    quantity: int
    price: Decimal
    course_title: str | None = None
    sku_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    order_sn: str
    total_amount: Decimal
    pay_amount: Decimal
    status: OrderStatus
    expire_time: datetime
    pay_time: datetime | None = None
    created_at: datetime
    items: list[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)


class OrderCreateResponse(BaseModel):
    order_sn: str
    total_amount: Decimal
    expire_time: datetime
    direct_granted: bool = False


class OrderListResponse(BaseModel):
    total: int
    items: list[OrderOut]


class PayCreateRequest(BaseModel):
    order_sn: str
    pay_method: Literal["wechat", "alipay"]


class PayCreateResponse(BaseModel):
    order_sn: str
    pay_method: str
    pay_url: str | None = None
    qr_code_url: str | None = None
    form: str | None = None
    mock: bool = True


class PayNotifyRequest(BaseModel):
    order_sn: str
    pay_method: Literal["wechat", "alipay"] | None = None
    trade_no: str | None = None
    status: str = "success"
    sign: str | None = None


class PayStatusResponse(BaseModel):
    order_sn: str
    status: OrderStatus
    paid: bool


class HealthCheck(BaseModel):
    status: str
    service: str


class SeckillActivityCreate(BaseModel):
    sku_id: int
    seckill_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    stock: int = Field(default=0, ge=0)
    limit_quantity: int = Field(default=1, ge=1)
    start_time: datetime
    end_time: datetime
    status: SeckillStatus = SeckillStatus.pending


class SeckillActivityRead(BaseModel):
    id: int
    sku_id: int
    seckill_price: Decimal
    stock: int
    limit_quantity: int
    start_time: datetime
    end_time: datetime
    status: SeckillStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeckillPreheatResponse(BaseModel):
    activity_id: int
    stock: int
    message: str


class SeckillQueueResponse(BaseModel):
    code: int = 200
    msg: str
    queue_id: str


class SeckillResultResponse(BaseModel):
    queue_id: str
    status: Literal["queued", "success", "failed"]
    order_sn: str | None = None
    message: str | None = None


class GenerateQuizRequest(BaseModel):
    course_id: int
    chapter_title: str = Field(min_length=1, max_length=200)
    knowledge_points: list[str] = Field(min_length=1)


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    answer: str


class GenerateQuizResponse(BaseModel):
    questions: list[QuizQuestion]
    mock: bool = False


class RecommendCoursesResponse(BaseModel):
    items: list[CourseRead]
    mock: bool = False


class GradeHomeworkRequest(BaseModel):
    homework_id: int
    student_answer: str = Field(min_length=1)


class GradeHomeworkResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    comment: str
    mock: bool = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64, description="对话会话ID，用于聊天记录")


class ChatResponse(BaseModel):
    answer: str
    mock: bool = False


class MyLearningCourseItem(BaseModel):
    id: int
    title: str
    cover: str | None = None
    category: str | None = None
    total_hours: int
    learn_count: int
    rating: float
    sku_id: int
    sku_name: str | None = None
    expire_date: datetime | None = None
    progress: int = 0
    is_trial: bool = False

    model_config = ConfigDict(from_attributes=True)


class MyLearningResponse(BaseModel):
    total: int
    items: list[MyLearningCourseItem]


class AdminUserOut(BaseModel):
    id: int
    username: str
    phone: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserOut]


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminCourseApprovalOut(BaseModel):
    id: int
    title: str
    teacher_id: int
    teacher_name: str | None = None
    category: str | None = None
    total_hours: int
    status: CourseStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCourseApprovalListResponse(BaseModel):
    total: int
    items: list[AdminCourseApprovalOut]


class AdminSeckillApprovalOut(BaseModel):
    id: int
    sku_id: int
    seckill_price: Decimal
    stock: int
    limit_quantity: int
    start_time: datetime
    end_time: datetime
    status: SeckillStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminSeckillApprovalListResponse(BaseModel):
    total: int
    items: list[AdminSeckillApprovalOut]


class AdminTeacherApprovalOut(BaseModel):
    id: int
    user_id: int
    username: str
    phone: str
    email: str
    name: str
    bio: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminTeacherApprovalListResponse(BaseModel):
    total: int
    items: list[AdminTeacherApprovalOut]


class LessonKnowledgeRead(BaseModel):
    id: int
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseKnowledgeRead(BaseModel):
    id: int
    course_id: int
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LessonRead(BaseModel):
    id: int
    title: str
    video_url: str | None = None
    duration: int
    sort_order: int
    is_locked: bool = False
    knowledge_files: list[LessonKnowledgeRead] = []

    model_config = ConfigDict(from_attributes=True)


class ChapterRead(BaseModel):
    id: int
    title: str
    sort_order: int
    lessons: list[LessonRead] = []

    model_config = ConfigDict(from_attributes=True)


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    sort_order: int | None = None


class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    video_url: str | None = None
    duration: int = Field(default=0, ge=0)
    sort_order: int = 0


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    video_url: str | None = None
    duration: int | None = Field(default=None, ge=0)
    sort_order: int | None = None


# ── Review / Rating ──

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)


class ReviewRead(BaseModel):
    id: int
    course_id: int
    user_id: int
    username: str | None = None
    rating: int
    content: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    total: int
    items: list[ReviewRead]
    average_rating: float
    review_count: int


# ── Upload ──

class UploadResponse(BaseModel):
    url: str
    filename: str
    size: int


# ── Admin Course Management ──

class AdminCourseCreate(BaseModel):
    teacher_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    cover: str | None = None
    category: str | None = Field(default=None, max_length=50)
    total_hours: int = Field(default=0, ge=0)


class AdminCourseListResponse(BaseModel):
    total: int
    items: list[CourseRead]


# ── Admin Review Management ──

class AdminReviewOut(BaseModel):
    id: int
    course_id: int
    course_title: str
    user_id: int
    username: str
    rating: int
    content: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminReviewListResponse(BaseModel):
    total: int
    items: list[AdminReviewOut]
