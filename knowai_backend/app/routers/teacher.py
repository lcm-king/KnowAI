from decimal import Decimal
from typing import Annotated
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_teacher
from app.config import settings
from app.crud import course_crud
from app.database import get_db
from app.models import Chapter, Course, CourseKnowledge, CourseSKU, CourseStatus, Lesson, LessonKnowledge, Order, OrderItem, OrderStatus, User
from app.schemas import (
    ChapterCreate,
    ChapterRead,
    ChapterUpdate,
    CourseCreate,
    CourseKnowledgeRead,
    CourseListResponse,
    CourseRead,
    CourseSKUCreate,
    CourseSKURead,
    CourseSKUUpdate,
    CourseUpdate,
    LessonCreate,
    LessonKnowledgeRead,
    LessonRead,
    LessonUpdate,
    SalesStatistics,
)
from app.services.knowledge_base import refresh_course_knowledge
from app.tasks.sync_es import sync_course_to_es

router = APIRouter()


async def get_teacher_or_404(db: AsyncSession, user: User):
    teacher = await course_crud.get_teacher_by_user_id(db, user.id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师信息不存在")
    return teacher


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseRead:
    teacher = await get_teacher_or_404(db, current_user)
    # Extract SKU fields before creating course (Course model doesn't have them)
    price = course_in.price
    stock = course_in.stock
    # Re-create with only Course fields
    course_data = course_in.model_dump(exclude={"price", "stock"}, exclude_none=True)
    course = Course(teacher_id=teacher.id, **course_data)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    # Auto-create SKU if price is provided
    if price is not None and price >= 0:
        sku_in = CourseSKUCreate(
            price=price,
            stock=stock or 0,
            validity_days=365,
        )
        await course_crud.create_course_sku(db, course.id, sku_in)
    # Auto-create first chapter and lesson if video_url is provided
    if course.video_url:
        max_order = await db.scalar(
            select(func.coalesce(func.max(Chapter.sort_order), -1)).where(Chapter.course_id == course.id)
        )
        chapter = Chapter(course_id=course.id, title="第一章", sort_order=int(max_order or 0) + 1)
        db.add(chapter)
        await db.flush()
        lesson = Lesson(
            chapter_id=chapter.id,
            title="第一节",
            video_url=course.video_url,
            duration=course.total_hours * 3600 if course.total_hours else 0,
            sort_order=0,
        )
        db.add(lesson)
    await db.commit()
    background_tasks.add_task(sync_course_to_es, course.id)
    return course


@router.put("/courses/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    course_in: CourseUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseRead:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    # Extract SKU fields and update course metadata
    sku_price = course_in.price
    sku_stock = course_in.stock
    course_data = course_in.model_dump(exclude={"price", "stock"}, exclude_unset=True)
    for key, value in course_data.items():
        setattr(course, key, value)
    await db.commit()
    await db.refresh(course)
    # Update or create SKU if price info was provided
    if sku_price is not None:
        existing = await course_crud.list_course_skus(db, course.id)
        if existing:
            sku = existing[0]
            await course_crud.update_course_sku(
                db, sku,
                CourseSKUUpdate(
                    price=sku_price,
                    stock=sku_stock if sku_stock is not None else sku.stock,
                    validity_days=365,
                ),
            )
        else:
            await course_crud.create_course_sku(
                db, course.id,
                CourseSKUCreate(
                    price=sku_price,
                    stock=sku_stock or 0,
                    validity_days=365,
                ),
            )
    background_tasks.add_task(sync_course_to_es, course.id)
    return course


@router.patch("/courses/{course_id}/submit", response_model=CourseRead)
async def submit_course(
    course_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseRead:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    # Auto-create first chapter if course has no chapters
    existing = await db.execute(select(Chapter).where(Chapter.course_id == course_id).limit(1))
    if existing.scalar_one_or_none() is None:
        chapter = Chapter(course_id=course_id, title="第一章", sort_order=1)
        db.add(chapter)
        await db.commit()
    course = await course_crud.submit_course(db, course)
    background_tasks.add_task(sync_course_to_es, course.id)
    return course


@router.patch("/courses/{course_id}/close", response_model=CourseRead)
async def close_course(
    course_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseRead:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    course = await course_crud.close_course(db, course)
    background_tasks.add_task(sync_course_to_es, course.id)
    return course


@router.post("/courses/{course_id}/skus", response_model=CourseSKURead, status_code=status.HTTP_201_CREATED)
async def create_course_sku(
    course_id: int,
    sku_in: CourseSKUCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseSKURead:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    sku = await course_crud.create_course_sku(db, course.id, sku_in)
    background_tasks.add_task(sync_course_to_es, course.id)
    return sku


@router.put("/skus/{sku_id}", response_model=CourseSKURead)
async def update_course_sku(
    sku_id: int,
    sku_in: CourseSKUUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseSKURead:
    teacher = await get_teacher_or_404(db, current_user)
    sku = await course_crud.get_teacher_sku(db, teacher.id, sku_id)
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU 不存在")
    sku = await course_crud.update_course_sku(db, sku, sku_in)
    background_tasks.add_task(sync_course_to_es, sku.course_id)
    return sku


@router.delete("/skus/{sku_id}", response_model=CourseSKURead)
async def delete_course_sku(
    sku_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> CourseSKURead:
    teacher = await get_teacher_or_404(db, current_user)
    sku = await course_crud.get_teacher_sku(db, teacher.id, sku_id)
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SKU 不存在")
    sku = await course_crud.delete_course_sku(db, sku)
    background_tasks.add_task(sync_course_to_es, sku.course_id)
    return sku


@router.get("/courses", response_model=CourseListResponse)
async def list_my_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: CourseStatus | None = Query(default=None, alias="status"),
) -> CourseListResponse:
    teacher = await get_teacher_or_404(db, current_user)
    total, courses = await course_crud.list_teacher_courses(db, teacher.id, page, page_size, status_filter)
    # Populate price info from first SKU
    items: list[CourseRead] = []
    for c in courses:
        course_read = CourseRead.model_validate(c)
        if c.skus:
            first_sku = c.skus[0]
            course_read.price = first_sku.price
            course_read.stock = first_sku.stock
            course_read.validity_days = first_sku.validity_days
        items.append(course_read)
    return CourseListResponse(total=total, items=items)


@router.get("/statistics/sales", response_model=SalesStatistics)
async def sales_statistics(
    current_user: Annotated[User, Depends(get_current_teacher)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SalesStatistics:
    teacher = await course_crud.get_teacher_by_user_id(db, current_user.id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师信息不存在")

    course_ids_stmt = select(Course.id).where(Course.teacher_id == teacher.id)
    course_ids_subq = course_ids_stmt.scalar_subquery()

    total_sales = await db.scalar(
        select(func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), Decimal("0.00")))
        .join(Order, Order.id == OrderItem.order_id)
        .join(CourseSKU, CourseSKU.id == OrderItem.sku_id)
        .where(
            CourseSKU.course_id.in_(course_ids_subq),
            Order.status.in_([OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
        )
    )
    order_count = await db.scalar(
        select(func.count(func.distinct(Order.id)))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(CourseSKU, CourseSKU.id == OrderItem.sku_id)
        .where(
            CourseSKU.course_id.in_(course_ids_subq),
            Order.status.in_([OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
        )
    )

    hot_stmt = (
        select(
            Course.id,
            Course.title,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("sold"),
        )
        .join(CourseSKU, CourseSKU.course_id == Course.id)
        .join(OrderItem, OrderItem.sku_id == CourseSKU.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Course.teacher_id == teacher.id,
            Order.status.in_([OrderStatus.paid, OrderStatus.learning, OrderStatus.completed]),
        )
        .group_by(Course.id, Course.title)
        .order_by(desc("sold"))
        .limit(5)
    )
    hot_result = await db.execute(hot_stmt)
    hot_courses = [
        {"id": row.id, "title": row.title, "sold": int(row.sold or 0)}
        for row in hot_result.all()
    ]

    return SalesStatistics(
        total_sales=Decimal(str(total_sales or 0)).quantize(Decimal("0.01")),
        order_count=int(order_count or 0),
        hot_courses=hot_courses,
    )


# ── Chapter CRUD ──────────────────────────────────────────────

@router.get("/courses/{course_id}/chapters", response_model=list[ChapterRead])
async def list_chapters(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> list[ChapterRead]:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    result = await db.execute(
        select(Chapter)
        .where(Chapter.course_id == course_id)
        .options(selectinload(Chapter.lessons).selectinload(Lesson.knowledge_files))
        .order_by(Chapter.sort_order)
    )
    chapters = result.scalars().all()
    return [ChapterRead.model_validate(c) for c in chapters]


@router.post("/courses/{course_id}/chapters", response_model=ChapterRead, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    course_id: int,
    chapter_in: ChapterCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> ChapterRead:
    teacher = await get_teacher_or_404(db, current_user)
    course = await course_crud.get_teacher_course(db, teacher.id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    max_order = await db.scalar(
        select(func.coalesce(func.max(Chapter.sort_order), -1)).where(Chapter.course_id == course_id)
    )
    chapter = Chapter(course_id=course_id, title=chapter_in.title, sort_order=int(max_order or 0) + 1)
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    # Eagerly load lessons to avoid async greenlet issue
    result = await db.execute(
        select(Chapter).where(Chapter.id == chapter.id).options(selectinload(Chapter.lessons).selectinload(Lesson.knowledge_files))
    )
    chapter = result.scalar_one()
    return ChapterRead.model_validate(chapter)


@router.put("/chapters/{chapter_id}", response_model=ChapterRead)
async def update_chapter(
    chapter_id: int,
    chapter_in: ChapterUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> ChapterRead:
    teacher = await get_teacher_or_404(db, current_user)
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.lessons).selectinload(Lesson.knowledge_files))
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    course = await course_crud.get_teacher_course(db, teacher.id, chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    if chapter_in.title is not None:
        chapter.title = chapter_in.title
    if chapter_in.sort_order is not None:
        chapter.sort_order = chapter_in.sort_order
    await db.commit()
    await db.refresh(chapter)
    return ChapterRead.model_validate(chapter)


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> dict[str, str]:
    teacher = await get_teacher_or_404(db, current_user)
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    course = await course_crud.get_teacher_course(db, teacher.id, chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    await db.delete(chapter)
    await db.commit()
    return {"status": "ok"}


# ── Lesson CRUD ────────────────────────────────────────────────

@router.post("/chapters/{chapter_id}/lessons", response_model=LessonRead, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    chapter_id: int,
    lesson_in: LessonCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> LessonRead:
    teacher = await get_teacher_or_404(db, current_user)
    result = await db.execute(
        select(Chapter).where(Chapter.id == chapter_id).options(selectinload(Chapter.course))
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    course = await course_crud.get_teacher_course(db, teacher.id, chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    lesson = Lesson(
        chapter_id=chapter_id,
        title=lesson_in.title,
        video_url=lesson_in.video_url,
        duration=lesson_in.duration,
        sort_order=lesson_in.sort_order,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    # Eagerly load knowledge_files to avoid async greenlet issue
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson.id).options(selectinload(Lesson.knowledge_files))
    )
    lesson = result.scalar_one()
    return LessonRead.model_validate(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonRead)
async def update_lesson(
    lesson_id: int,
    lesson_in: LessonUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> LessonRead:
    teacher = await get_teacher_or_404(db, current_user)
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.chapter).selectinload(Chapter.course))
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课时不存在")
    course = await course_crud.get_teacher_course(db, teacher.id, lesson.chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    if lesson_in.title is not None:
        lesson.title = lesson_in.title
    if lesson_in.video_url is not None:
        lesson.video_url = lesson_in.video_url
    if lesson_in.duration is not None:
        lesson.duration = lesson_in.duration
    if lesson_in.sort_order is not None:
        lesson.sort_order = lesson_in.sort_order
    await db.commit()
    # Eagerly load knowledge_files to avoid async greenlet issue
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.knowledge_files))
    )
    lesson = result.scalar_one()
    return LessonRead.model_validate(lesson)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> dict[str, str]:
    teacher = await get_teacher_or_404(db, current_user)
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.chapter).selectinload(Chapter.course))
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课时不存在")
    course = await course_crud.get_teacher_course(db, teacher.id, lesson.chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    await db.delete(lesson)
    await db.commit()
    return {"status": "ok"}


# ── Course Knowledge Base CRUD ──────────────────────────────────────


async def _get_course_for_teacher(db: AsyncSession, teacher_id: int, course_id: int) -> Course:
    course = await course_crud.get_teacher_course(db, teacher_id, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    return course


@router.get("/courses/{course_id}/knowledge", response_model=list[CourseKnowledgeRead])
async def list_course_knowledge(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> list[CourseKnowledgeRead]:
    teacher = await get_teacher_or_404(db, current_user)
    await _get_course_for_teacher(db, teacher.id, course_id)
    result = await db.execute(
        select(CourseKnowledge)
        .where(CourseKnowledge.course_id == course_id)
        .order_by(CourseKnowledge.created_at.desc())
    )
    return [CourseKnowledgeRead.model_validate(k) for k in result.scalars().all()]


@router.post("/courses/{course_id}/knowledge", response_model=CourseKnowledgeRead, status_code=status.HTTP_201_CREATED)
async def upload_course_knowledge(
    course_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
    file: UploadFile = File(...),
) -> CourseKnowledgeRead:
    teacher = await get_teacher_or_404(db, current_user)
    await _get_course_for_teacher(db, teacher.id, course_id)

    allowed = {"application/pdf", "text/plain", "text/markdown", "application/msword",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文档格式，仅支持 PDF/TXT/Markdown/DOC")
    content_bytes = await file.read()
    if len(content_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档大小超过 50MB 限制")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_dir = settings.upload_dir / "documents"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / filename).write_bytes(content_bytes)
    file_url = f"{settings.api_prefix}/uploads/documents/{filename}"

    text_content: str | None = None
    if file.content_type in ("text/plain", "text/markdown"):
        text_content = content_bytes.decode("utf-8", errors="replace")

    knowledge = CourseKnowledge(
        course_id=course_id,
        file_name=file.filename or "document",
        file_url=file_url,
        file_type=file.content_type or "application/octet-stream",
        file_size=len(content_bytes),
        content=text_content,
    )
    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)
    background_tasks.add_task(refresh_course_knowledge, course_id, db)
    return CourseKnowledgeRead.model_validate(knowledge)


@router.delete("/courses/{course_id}/knowledge/{knowledge_id}")
async def delete_course_knowledge(
    course_id: int,
    knowledge_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> dict[str, str]:
    teacher = await get_teacher_or_404(db, current_user)
    await _get_course_for_teacher(db, teacher.id, course_id)
    result = await db.execute(
        select(CourseKnowledge).where(CourseKnowledge.id == knowledge_id, CourseKnowledge.course_id == course_id)
    )
    knowledge = result.scalar_one_or_none()
    if knowledge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库文件不存在")

    try:
        rel_path = knowledge.file_url.replace(f"{settings.api_prefix}/uploads/", "", 1)
        file_path = settings.upload_dir / rel_path
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass

    await db.delete(knowledge)
    await db.commit()
    background_tasks.add_task(refresh_course_knowledge, course_id, db)
    return {"status": "ok"}


# ── Lesson Knowledge Base CRUD ──────────────────────────────────


async def _get_lesson_for_teacher(db: AsyncSession, teacher_id: int, lesson_id: int) -> Lesson:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.chapter).selectinload(Chapter.course))
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课时不存在")
    course = await course_crud.get_teacher_course(db, teacher_id, lesson.chapter.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程")
    return lesson


@router.get("/lessons/{lesson_id}/knowledge", response_model=list[LessonKnowledgeRead])
async def list_lesson_knowledge(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> list[LessonKnowledgeRead]:
    teacher = await get_teacher_or_404(db, current_user)
    await _get_lesson_for_teacher(db, teacher.id, lesson_id)
    result = await db.execute(
        select(LessonKnowledge)
        .where(LessonKnowledge.lesson_id == lesson_id)
        .order_by(LessonKnowledge.created_at.desc())
    )
    return [LessonKnowledgeRead.model_validate(k) for k in result.scalars().all()]


@router.post("/lessons/{lesson_id}/knowledge", response_model=LessonKnowledgeRead, status_code=status.HTTP_201_CREATED)
async def upload_lesson_knowledge(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
    file: UploadFile = File(...),
) -> LessonKnowledgeRead:
    teacher = await get_teacher_or_404(db, current_user)
    lesson = await _get_lesson_for_teacher(db, teacher.id, lesson_id)

    allowed = {"application/pdf", "text/plain", "text/markdown", "application/msword",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文档格式，仅支持 PDF/TXT/Markdown/DOC")
    content_bytes = await file.read()
    if len(content_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档大小超过 50MB 限制")

    # Save file to disk
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_dir = settings.upload_dir / "documents"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / filename).write_bytes(content_bytes)
    file_url = f"{settings.api_prefix}/uploads/documents/{filename}"

    # Extract text content from TXT/MD files
    text_content: str | None = None
    if file.content_type in ("text/plain", "text/markdown"):
        text_content = content_bytes.decode("utf-8", errors="replace")

    knowledge = LessonKnowledge(
        lesson_id=lesson_id,
        file_name=file.filename or "document",
        file_url=file_url,
        file_type=file.content_type or "application/octet-stream",
        file_size=len(content_bytes),
        content=text_content,
    )
    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)
    background_tasks.add_task(refresh_course_knowledge, lesson.chapter.course_id, db)
    return LessonKnowledgeRead.model_validate(knowledge)


@router.delete("/lessons/{lesson_id}/knowledge/{knowledge_id}")
async def delete_lesson_knowledge(
    lesson_id: int,
    knowledge_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_teacher)],
) -> dict[str, str]:
    teacher = await get_teacher_or_404(db, current_user)
    lesson = await _get_lesson_for_teacher(db, teacher.id, lesson_id)
    result = await db.execute(
        select(LessonKnowledge).where(LessonKnowledge.id == knowledge_id, LessonKnowledge.lesson_id == lesson_id)
    )
    knowledge = result.scalar_one_or_none()
    if knowledge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库文件不存在")

    # Delete file from disk
    try:
        rel_path = knowledge.file_url.replace(f"{settings.api_prefix}/uploads/", "", 1)
        file_path = settings.upload_dir / rel_path
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass  # Non-critical: file may already be deleted

    await db.delete(knowledge)
    await db.commit()
    background_tasks.add_task(refresh_course_knowledge, lesson.chapter.course_id, db)
    return {"status": "ok"}
