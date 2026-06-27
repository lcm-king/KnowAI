"""
New AI endpoints powered by LangChain + LangGraph multi-agent workflows.

Replaces the Dify-based implementation while keeping the old endpoints
as deprecated wrappers for backward compatibility.

Endpoints
---------
- ``POST /ai/knowledge/recommend`` — Course recommendation with intent parsing
- ``POST /ai/knowledge/quiz`` — Quiz generation from knowledge base
- ``POST /ai/knowledge/grade`` — Homework grading with reference retrieval
- ``POST /ai/knowledge/chat`` — Conversational AI assistant
- ``POST /ai/knowledge/refresh/{course_id}`` — Trigger vector index rebuild
"""

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db, get_mongo
from app.models import Course, CourseStatus, Teacher, User, UserCourse
from app.schemas import (
    ChatRequest,
    ChatResponse,
    CourseRead,
    GenerateQuizRequest,
    GenerateQuizResponse,
    GradeHomeworkRequest,
    GradeHomeworkResponse,
    QuizQuestion,
    RecommendCoursesResponse,
)
from app.services.knowledge_base import kb_manager, refresh_course_knowledge
from app.services.langgraph_workflow import workflow

logger = logging.getLogger("knowai.ai_new")
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════

def _course_to_read(course: Course) -> CourseRead:
    """Convert a Course ORM instance to a CourseRead schema."""
    teacher_name: str | None = None
    if course.teacher:
        teacher_name = course.teacher.name
    return CourseRead(
        id=course.id,
        teacher_id=course.teacher_id,
        teacher_name=teacher_name,
        title=course.title,
        description=course.description,
        cover=course.cover,
        category=course.category,
        total_hours=course.total_hours,
        learn_count=course.learn_count,
        rating=course.rating,
        status=course.status,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def _get_skus_info(course: Course) -> dict[str, Any]:
    """Extract price and stock from the first published SKU."""
    for sku in course.skus:
        if sku.status.value == "on":
            return {"price": sku.price, "stock": sku.stock}
    return {"price": None, "stock": None}


# ═══════════════════════════════════════════════════════════════════
# 1. Course Recommendation
# ═══════════════════════════════════════════════════════════════════

class RecommendRequest(BaseModel):
    """Request body for the knowledge-based recommendation endpoint."""
    description: str = Field(..., min_length=1, max_length=2000, description="用户学习需求描述")
    goal: str | None = Field(default=None, max_length=1000, description="学习目标")
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/knowledge/recommend", response_model=RecommendCoursesResponse)
async def recommend_courses_knowledge(
    payload: RecommendRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendCoursesResponse:
    """推荐课程：基于用户描述+知识库RAG的多Agent工作流。

    替代原有的 ``POST /ai/recommend_courses``（已弃用）。
    """
    user_input = payload.description
    if payload.goal:
        user_input = f"{user_input}，目标：{payload.goal}"

    # 1. Get owned course IDs to exclude
    owned_result = await db.execute(
        select(UserCourse.course_id).where(UserCourse.user_id == current_user.id)
    )
    owned_ids = set(owned_result.scalars().all())

    # 2. Fetch all published courses from DB (candidates)
    result = await db.execute(
        select(Course)
        .where(Course.status == CourseStatus.published)
        .options(selectinload(Course.teacher), selectinload(Course.skus))
        .order_by(desc(Course.learn_count))
        .limit(50)
    )
    all_courses = list(result.scalars().all())

    # 3. Build candidate course metadata for the workflow
    candidate_courses = [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description or "",
            "category": c.category or "",
        }
        for c in all_courses if c.id not in owned_ids
    ]

    # 4. Run LangGraph recommendation workflow
    #    The graph parses intent, retrieves from vector DB, ranks
    wf_result = await workflow.run_recommend(
        user_input=user_input,
        course_ids=[c["id"] for c in candidate_courses],
        candidate_courses=candidate_courses,
    )

    recommended_ids = [
        r["course_id"] for r in wf_result.get("recommendations", [])
        if isinstance(r, dict) and r.get("course_id")
    ]

    # 5. If no recommendations from graph, fall back to hot courses
    if not recommended_ids:
        recommended_ids = [c.id for c in all_courses[:10] if c.id not in owned_ids]

    # 6. Build response
    course_map = {c.id: c for c in all_courses}
    items: list[CourseRead] = []
    for cid in recommended_ids:
        if cid in owned_ids:
            continue
        course = course_map.get(cid)
        if course:
            items.append(_course_to_read(course))
        if len(items) >= payload.limit:
            break

    return RecommendCoursesResponse(items=items, mock=False)


# ═══════════════════════════════════════════════════════════════════
# 2. Quiz Generation
# ═══════════════════════════════════════════════════════════════════

class QuizRequest(BaseModel):
    """Request body for knowledge-based quiz generation."""
    course_id: int
    chapter_title: str = Field(min_length=1, max_length=200)
    knowledge_points: list[str] = Field(min_length=1)
    lesson_id: int | None = None
    question_types: list[str] | None = Field(default=None, description="题型：选择题、问答题")
    difficulty: str = Field(default="中等")
    count: int = Field(default=5, ge=1, le=20)


@router.post("/knowledge/quiz", response_model=GenerateQuizResponse)
async def generate_quiz_knowledge(
    payload: QuizRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GenerateQuizResponse:
    """智能出题：基于知识库RAG的多Agent工作流生成测验题目。

    替代原有的 ``POST /ai/generate_quiz``（已弃用）。
    """
    result = await workflow.run_quiz_generation(
        course_id=payload.course_id,
        chapter_title=payload.chapter_title,
        knowledge_points=payload.knowledge_points,
        lesson_id=payload.lesson_id,
        question_types=payload.question_types,
        difficulty=payload.difficulty,
        count=payload.count,
    )

    questions = []
    for q in result.get("questions", []):
        questions.append(QuizQuestion(
            question=q.get("question", ""),
            options=q.get("options", []),
            answer=q.get("answer", ""),
        ))

    return GenerateQuizResponse(questions=questions, mock=result.get("mock", False))


# ═══════════════════════════════════════════════════════════════════
# 3. Homework Grading
# ═══════════════════════════════════════════════════════════════════

class GradeRequest(BaseModel):
    """Request body for knowledge-based homework grading."""
    question: str = Field(min_length=1, description="题目内容")
    student_answer: str = Field(min_length=1, description="学生答案")
    course_id: int | None = Field(default=None, description="关联课程ID（用于检索参考知识点）")


@router.post("/knowledge/grade", response_model=GradeHomeworkResponse)
async def grade_homework_knowledge(
    payload: GradeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GradeHomeworkResponse:
    """批改作业：基于知识库RAG的多Agent工作流。

    替代原有的 ``POST /ai/grade_homework``（已弃用）。
    """
    result = await workflow.run_grading(
        question=payload.question,
        student_answer=payload.student_answer,
        course_id=payload.course_id,
    )
    return GradeHomeworkResponse(
        score=int(result.get("score", 0)),
        comment=str(result.get("comment", "")),
        mock=result.get("mock", False),
    )


# ═══════════════════════════════════════════════════════════════════
# 4. Chat
# ═══════════════════════════════════════════════════════════════════

@router.post("/knowledge/chat", response_model=ChatResponse)
async def chat_knowledge(
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatResponse:
    """对话助手：搜索知识库 + 联网搜索 + 聊天记录 + AI 大模型兜底。

    流程：
    1. 搜索所有课程知识库
    2. 联网搜索实时信息（天气、新闻等）
    3. 加载聊天历史
    4. 调用大模型生成回答（绝不拒绝回答）
    """
    from datetime import datetime, timezone

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from app.config import settings
    from app.services.web_search import search_web

    # ── 1. Search all course knowledge bases ──
    course_result = await db.execute(
        select(Course.id).where(Course.status == CourseStatus.published)
    )
    all_course_ids = list(course_result.scalars().all())

    kb_context = ""
    source_courses: set[str] = set()
    if all_course_ids:
        docs = kb_manager.search_all_courses(payload.message, all_course_ids, k_per_course=2)
        for d in docs:
            kb_context += d.page_content + "\n"
            cid = d.metadata.get("course_id")
            if cid:
                source_courses.add(str(cid))

    # ── 2. Web search for real-time information ──
    web_results = search_web(payload.message, max_results=5)

    # ── 3. Build context parts ──
    context_parts: list[str] = []
    if kb_context:
        source_hint = ""
        if source_courses:
            source_hint = f"（相关课程ID：{', '.join(source_courses)}）"
        context_parts.append(f"【课程知识库内容{source_hint}】\n{kb_context}")

    if web_results:
        web_text = "\n".join(
            f"- {r['title']}: {r['body']}" for r in web_results if r.get("title") or r.get("body")
        )
        context_parts.append(f"【联网搜索结果】\n{web_text}")

    # ── 4. Get chat history from MongoDB ──
    session_id = payload.session_id
    history_messages: list[dict] = []
    if session_id:
        try:
            mongo = await get_mongo()
            cursor = mongo.chat_messages.find(
                {"user_id": current_user.id, "session_id": session_id},
                sort=[("created_at", 1)],
                limit=20,
            )
            history_messages = await cursor.to_list(length=20)
        except Exception:
            logger.warning("Failed to load chat history from MongoDB", exc_info=True)

    # ── 5. Build LLM prompt ──
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url or None,
        temperature=0.7,
    )

    system_content = (
        "你是一个智能AI学习助手「学伴」，由知学AI平台提供。\n"
        "关于你自己：\n"
        "- 你的名字叫「学伴」，是一个专注于学习辅导的AI助手\n"
        "- 如果用户问「你是谁」或类似问题，请直接介绍自己是学伴\n"
        "核心原则：\n"
        "- 你必须回答用户的每一个问题，绝不能说「不知道」或「无法回答」\n"
        "- 如果课程知识库中有相关内容，优先基于知识库回答\n"
        "- 如果有联网搜索结果，结合搜索结果回答实时信息（天气、新闻等）\n"
        "- 如果以上都没有，使用你自己的知识自信回答\n"
        "- 提及课程名称时请使用《》括起来\n"
        "- 回答要简洁、准确、有用，用中文回复"
    )

    messages = [SystemMessage(content=system_content)]

    # Add chat history (last 10 turns)
    for hm in history_messages[-10:]:
        role = hm.get("role", "")
        content = hm.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=f"[历史消息] {content}"))
        elif role == "assistant":
            messages.append(SystemMessage(content=f"[历史回复] {content}"))

    # Add context from KB and web
    if context_parts:
        combined = "\n\n".join(context_parts)
        messages.append(HumanMessage(content=f"以下是参考信息，请基于这些内容回答问题：\n\n{combined}"))
    else:
        messages.append(HumanMessage(content="没有找到相关参考信息，请根据你自己的知识直接回答用户的问题。"))

    messages.append(HumanMessage(content=payload.message))

    # ── 6. Call LLM ──
    try:
        response = await llm.ainvoke(messages)
        answer = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as exc:
        logger.warning("Chat LLM call failed: %s", exc)
        answer = "抱歉，AI助手暂时无法回复，请稍后再试。"
        return ChatResponse(answer=answer, mock=True)

    # ── 7. Save chat history ──
    if session_id:
        try:
            mongo = await get_mongo()
            now = datetime.now(timezone.utc)
            await mongo.chat_messages.insert_many([
                {"user_id": current_user.id, "session_id": session_id, "role": "user", "content": payload.message, "created_at": now},
                {"user_id": current_user.id, "session_id": session_id, "role": "assistant", "content": answer, "created_at": now},
            ])
            # Upsert session metadata
            await mongo.chat_sessions.update_one(
                {"user_id": current_user.id, "session_id": session_id},
                {
                    "$set": {"updated_at": now},
                    "$setOnInsert": {
                        "title": payload.message[:80],
                        "created_at": now,
                    },
                },
                upsert=True,
            )
        except Exception:
            logger.warning("Failed to save chat history to MongoDB", exc_info=True)

    return ChatResponse(answer=answer, mock=False)


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    messages: list[dict[str, str]] = []


@router.get("/knowledge/chat/history", response_model=ChatHistoryResponse)
async def chat_history(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatHistoryResponse:
    """获取对话历史记录。"""
    try:
        mongo = await get_mongo()
        cursor = mongo.chat_messages.find(
            {"user_id": current_user.id, "session_id": session_id},
            sort=[("created_at", 1)],
            limit=50,
        )
        docs = await cursor.to_list(length=50)
        messages_list = [{"role": d["role"], "content": d["content"]} for d in docs]
    except Exception:
        logger.warning("Failed to load chat history", exc_info=True)
        messages_list = []
    return ChatHistoryResponse(messages=messages_list)


class ChatSessionItem(BaseModel):
    """A chat session summary."""
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionItem] = []


@router.get("/knowledge/chat/sessions", response_model=ChatSessionListResponse)
async def chat_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatSessionListResponse:
    """获取用户的对话会话列表。"""
    try:
        mongo = await get_mongo()
        cursor = mongo.chat_sessions.find(
            {"user_id": current_user.id},
            sort=[("updated_at", -1)],
            limit=50,
        )
        docs = await cursor.to_list(length=50)
        sessions = []
        for d in docs:
            # Count messages for this session
            msg_count = await mongo.chat_messages.count_documents(
                {"user_id": current_user.id, "session_id": d["session_id"]}
            )
            sessions.append(ChatSessionItem(
                session_id=d["session_id"],
                title=d.get("title", "新会话"),
                created_at=d.get("created_at", d["updated_at"]),
                updated_at=d["updated_at"],
                message_count=msg_count,
            ))
    except Exception:
        logger.warning("Failed to load chat sessions", exc_info=True)
        sessions = []
    return ChatSessionListResponse(sessions=sessions)


@router.delete("/knowledge/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """删除对话会话及其所有消息。"""
    try:
        mongo = await get_mongo()
        await mongo.chat_messages.delete_many({"user_id": current_user.id, "session_id": session_id})
        await mongo.chat_sessions.delete_one({"user_id": current_user.id, "session_id": session_id})
    except Exception:
        logger.warning("Failed to delete chat session", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "deleted"}


# ═══════════════════════════════════════════════════════════════════
# 5. Knowledge Index Refresh
# ═══════════════════════════════════════════════════════════════════

@router.post("/knowledge/refresh/{course_id}")
async def refresh_knowledge_index(
    course_id: int,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """触发指定课程的向量索引重建（后台任务）。

    教师用户只能刷新自己的课程；管理员可刷新任意课程。
    """
    # Permission check
    if current_user.role.value == "admin":
        course = await db.get(Course, course_id)
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    elif current_user.role.value == "teacher":
        from app.crud import course_crud
        teacher = await course_crud.get_teacher_by_user_id(db, current_user.id)
        if teacher is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅讲师可操作")
        course = await course_crud.get_teacher_course(db, teacher.id, course_id)
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在或无权限")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")

    background_tasks.add_task(refresh_course_knowledge, course_id, db)
    return {"status": "started", "course_id": course_id, "message": "向量索引重建已启动"}


# ═══════════════════════════════════════════════════════════════════
# Deprecated Old Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/generate_quiz", response_model=GenerateQuizResponse, deprecated=True)
async def generate_course_quiz_deprecated(
    payload: GenerateQuizRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GenerateQuizResponse:
    """已弃用，请使用 ``POST /ai/knowledge/quiz``。"""
    result = await workflow.run_quiz_generation(
        course_id=payload.course_id,
        chapter_title=payload.chapter_title,
        knowledge_points=payload.knowledge_points,
    )
    questions = [QuizQuestion(**q) for q in result.get("questions", [])]
    return GenerateQuizResponse(questions=questions, mock=result.get("mock", False))


@router.post("/recommend_courses", response_model=RecommendCoursesResponse, deprecated=True)
async def recommend_courses_deprecated(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendCoursesResponse:
    """已弃用，请使用 ``POST /ai/knowledge/recommend``。"""
    owned_result = await db.execute(
        select(UserCourse.course_id).where(UserCourse.user_id == current_user.id)
    )
    owned_ids = set(owned_result.scalars().all())

    hot_result = await db.execute(
        select(Course)
        .where(Course.status == CourseStatus.published)
        .order_by(desc(Course.learn_count))
        .limit(10)
    )
    courses = list(hot_result.scalars().all())
    items = [_course_to_read(c) for c in courses if c.id not in owned_ids]
    return RecommendCoursesResponse(items=items, mock=True)


@router.post("/grade_homework", response_model=GradeHomeworkResponse, deprecated=True)
async def grade_homework_deprecated(
    payload: GradeHomeworkRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> GradeHomeworkResponse:
    """已弃用，请使用 ``POST /ai/knowledge/grade``。"""
    result = await workflow.run_grading(
        question=f"作业 #{payload.homework_id}",
        student_answer=payload.student_answer,
    )
    return GradeHomeworkResponse(
        score=int(result.get("score", 0)),
        comment=str(result.get("comment", "")),
        mock=result.get("mock", False),
    )
