from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db, get_mongo
from app.models import Course, CourseStatus, User, UserCourse
from app.schemas import (
    ChatRequest,
    ChatResponse,
    GenerateQuizRequest,
    GenerateQuizResponse,
    GradeHomeworkRequest,
    GradeHomeworkResponse,
    QuizQuestion,
    RecommendCoursesResponse,
)
from app.services.dify_client import chat_with_assistant, generate_quiz, grade_homework, recommend_courses

router = APIRouter()


@router.post("/generate_quiz", response_model=GenerateQuizResponse)
async def generate_course_quiz(
    payload: GenerateQuizRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenerateQuizResponse:
    course = await db.get(Course, payload.course_id)
    chapter_content = f"课程《{course.title if course else payload.course_id}》章节《{payload.chapter_title}》的模拟章节内容。"
    questions, mock = await generate_quiz(
        {
            "course_id": payload.course_id,
            "chapter_title": payload.chapter_title,
            "chapter_content": chapter_content,
            "knowledge_points": payload.knowledge_points,
        },
        str(current_user.id),
    )
    return GenerateQuizResponse(questions=[QuizQuestion.model_validate(question) for question in questions], mock=mock)


@router.post("/recommend_courses", response_model=RecommendCoursesResponse)
async def recommend_user_courses(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    mongo: Annotated[AsyncIOMotorDatabase, Depends(get_mongo)],
) -> RecommendCoursesResponse:
    browse_doc = await mongo.user_browse_history.find_one({"user_id": current_user.id})
    recent_course_ids = browse_doc.get("course_ids", []) if browse_doc else []

    owned_result = await db.execute(select(UserCourse.course_id).where(UserCourse.user_id == current_user.id))
    owned_course_ids = list(owned_result.scalars().all())

    hot_result = await db.execute(
        select(Course)
        .where(Course.status == CourseStatus.published)
        .order_by(desc(Course.learn_count), desc(Course.created_at))
        .limit(10)
    )
    hot_courses = list(hot_result.scalars().all())
    hot_course_ids = [course.id for course in hot_courses]

    recommended_ids, mock = await recommend_courses(
        {
            "user_id": current_user.id,
            "recent_course_ids": recent_course_ids,
            "owned_course_ids": owned_course_ids,
            "hot_course_ids": hot_course_ids,
        },
        str(current_user.id),
    )

    ids = [course_id for course_id in recommended_ids if course_id not in owned_course_ids]
    if not ids:
        ids = [course_id for course_id in hot_course_ids if course_id not in owned_course_ids]
    if not ids:
        return RecommendCoursesResponse(items=[], mock=mock)

    courses_result = await db.execute(select(Course).where(Course.id.in_(ids), Course.status == CourseStatus.published))
    course_map = {course.id: course for course in courses_result.scalars().all()}
    courses = [course_map[course_id] for course_id in ids if course_id in course_map]
    return RecommendCoursesResponse(items=courses, mock=mock)


@router.post("/grade_homework", response_model=GradeHomeworkResponse)
async def grade_student_homework(
    payload: GradeHomeworkRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GradeHomeworkResponse:
    question_content = f"作业 {payload.homework_id} 的模拟题目内容。"
    result, mock = await grade_homework(
        {
            "homework_id": payload.homework_id,
            "question_content": question_content,
            "student_answer": payload.student_answer,
        },
        str(current_user.id),
    )
    return GradeHomeworkResponse(score=int(result.get("score", 0)), comment=str(result.get("comment", "")), mock=mock)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant_endpoint(
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatResponse:
    answer, mock = await chat_with_assistant(payload.message, str(current_user.id))
    return ChatResponse(answer=answer, mock=mock)
