from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_current_user_optional
from app.database import get_db
from app.models import Course, CourseAnswer, CourseQuestion, Teacher, User
from app.schemas import AnswerCreate, AnswerRead, QuestionCreate, QuestionDetailRead, QuestionRead

router = APIRouter()


@router.get("/questions", response_model=list[QuestionRead])
async def list_questions(
    db: Annotated[AsyncSession, Depends(get_db)],
    course_id: Annotated[int, Query(ge=1)],
    lesson_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[QuestionRead]:
    stmt = (
        select(CourseQuestion)
        .where(CourseQuestion.course_id == course_id)
        .order_by(CourseQuestion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if lesson_id is not None:
        stmt = stmt.where(CourseQuestion.lesson_id == lesson_id)
    result = await db.execute(stmt)
    questions = list(result.scalars().all())

    # Get answer counts
    q_ids = [q.id for q in questions]
    items: list[QuestionRead] = []
    if q_ids:
        count_result = await db.execute(
            select(CourseAnswer.question_id, func.count(CourseAnswer.id))
            .where(CourseAnswer.question_id.in_(q_ids))
            .group_by(CourseAnswer.question_id)
        )
        count_map = dict(count_result.all())

        user_ids = list(set(q.user_id for q in questions))
        user_result = await db.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
        user_map = dict(user_result.all())

        for q in questions:
            items.append(
                QuestionRead(
                    id=q.id,
                    course_id=q.course_id,
                    lesson_id=q.lesson_id,
                    user_id=q.user_id,
                    username=user_map.get(q.user_id),
                    title=q.title,
                    content=q.content,
                    created_at=q.created_at,
                    answer_count=count_map.get(q.id, 0),
                )
            )
    return items


@router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestionRead:
    question = CourseQuestion(
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return QuestionRead(
        id=question.id,
        course_id=question.course_id,
        lesson_id=question.lesson_id,
        user_id=question.user_id,
        username=current_user.username,
        title=question.title,
        content=question.content,
        created_at=question.created_at,
    )


@router.get("/questions/{question_id}", response_model=QuestionDetailRead)
async def get_question_detail(
    question_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionDetailRead:
    result = await db.execute(
        select(CourseQuestion)
        .where(CourseQuestion.id == question_id)
        .options(selectinload(CourseQuestion.answers))
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")
    return QuestionDetailRead(
        id=question.id,
        course_id=question.course_id,
        lesson_id=question.lesson_id,
        user_id=question.user_id,
        username="",
        title=question.title,
        content=question.content,
        created_at=question.created_at,
        answer_count=len(question.answers),
        answers=[
            AnswerRead(
                id=a.id,
                question_id=a.question_id,
                user_id=a.user_id,
                username="",
                content=a.content,
                is_teacher_answer=a.is_teacher_answer,
                created_at=a.created_at,
            )
            for a in question.answers
        ],
    )


@router.post("/questions/{question_id}/answers", response_model=AnswerRead, status_code=status.HTTP_201_CREATED)
async def create_answer(
    question_id: int,
    payload: AnswerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnswerRead:
    # Verify question exists
    result = await db.execute(select(CourseQuestion).where(CourseQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")

    # Check if current user is a teacher of this course
    is_teacher = False
    if current_user.teacher_id is not None:
        t_course = await db.execute(
            select(Course.id).where(Course.id == question.course_id, Course.teacher_id == current_user.teacher_id).limit(1)
        )
        is_teacher = t_course.scalar_one_or_none() is not None

    answer = CourseAnswer(
        question_id=question_id,
        user_id=current_user.id,
        content=payload.content,
        is_teacher_answer=is_teacher,
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)
    return AnswerRead(
        id=answer.id,
        question_id=answer.question_id,
        user_id=answer.user_id,
        username=current_user.username,
        content=answer.content,
        is_teacher_answer=answer.is_teacher_answer,
        created_at=answer.created_at,
    )
