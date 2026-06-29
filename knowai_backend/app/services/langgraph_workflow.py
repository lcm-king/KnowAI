"""
LangGraph Multi-Agent Workflows for the "学伴" AI learning companion.

Three workflows:
1. **Course Recommendation** — parse user intent → retrieve courses + RAG → rank
2. **Quiz Generation** — retrieve content → generate → validate
3. **Homework Grading** — retrieve reference → grade → feedback

Each workflow is a separate compiled :class:`StateGraph` exposed through the
:class:`LangGraphWorkflow` facade.
"""

import json
import logging
import re
from typing import Annotated, Any, Literal

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.config import settings
from app.services.knowledge_base import kb_manager

logger = logging.getLogger("knowai.langgraph_workflow")

# ═══════════════════════════════════════════════════════════════════
# LLM
# ═══════════════════════════════════════════════════════════════════

def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url or None,
        temperature=0.3,
    )


# ═══════════════════════════════════════════════════════════════════
# Shared Tools
# ═══════════════════════════════════════════════════════════════════

@tool
def retrieve_knowledge(query: str, course_id: int) -> str:
    """Search the vector knowledge base for content relevant to the query.

    Returns up to 5 document excerpts with metadata.
    """
    docs = kb_manager.search_similar(query, course_id=course_id, k=5)
    if not docs:
        return "未找到相关知识点内容。"
    lines: list[str] = []
    for i, d in enumerate(docs, 1):
        meta = d.metadata
        source = meta.get("file_name", "未知")
        lesson = meta.get("lesson_id", "0")
        tag = f"  [来自: {source}" + (f" / 课时 {lesson}" if lesson != "0" else "") + "]"
        lines.append(f"{i}. {d.page_content}{tag}")
    return "\n\n".join(lines)


@tool
def search_courses(
    keywords: str,
    category: str | None = None,
    min_rating: float = 0.0,
    limit: int = 10,
) -> str:
    """Search published courses in the MySQL database.

    Returns course id, title, category, rating and sales count as JSON.
    (This tool stores query intent; actual DB query is done by the node.)
    """
    return json.dumps({"keywords": keywords, "category": category, "min_rating": min_rating, "limit": limit})


# ═══════════════════════════════════════════════════════════════════
# ── 1. COURSE RECOMMENDATION WORKFLOW ──
# ═══════════════════════════════════════════════════════════════════

class IntentOutput(BaseModel):
    """Structured output from the intent parser."""
    skills: list[str] = Field(description="关键技术/技能关键词")
    goals: list[str] = Field(description="学习目标")
    time_hint: str | None = Field(description="时间需求描述，如'三个月'")
    level: Literal["beginner", "intermediate", "advanced"] = Field(description="用户当前水平")


class RecommendState(TypedDict):
    user_input: str
    parsed_intent: dict[str, Any]
    course_ids: list[int]
    candidate_courses: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    messages: list[BaseMessage]
    error: str | None


def parse_intent_node(state: RecommendState) -> dict[str, Any]:
    """Agent 1: Parse user input into structured learning intent."""
    system_prompt = SystemMessage(
        content="你是一个学习意图分析助手。请从用户描述中提取技能关键词、学习目标、时间需求和学习水平。"
    )
    user_msg = HumanMessage(content=f"用户学习需求：{state['user_input']}")
    llm = _llm().with_structured_output(IntentOutput, method="function_calling")
    try:
        result: IntentOutput = llm.invoke([system_prompt, user_msg])  # type: ignore[assignment]
        parsed = result.model_dump()
    except Exception as exc:
        logger.warning("Intent parsing failed, using fallback: %s", exc)
        parsed = {"skills": [state["user_input"]], "goals": [], "time_hint": None, "level": "beginner"}

    return {"parsed_intent": parsed}


def retrieve_courses_node(state: RecommendState) -> dict[str, Any]:
    """Agent 2: Retrieve candidate courses from vector DB and prepare search query."""
    parsed = state["parsed_intent"]
    skills = " ".join(parsed.get("skills", []))
    goals = " ".join(parsed.get("goals", []))

    search_query = f"{skills} {goals}".strip() or state["user_input"]

    # Actually query the vector database for relevant content
    course_ids = state.get("course_ids", [])
    retrieved_chunks = []
    if course_ids:
        docs = kb_manager.search_all_courses(search_query, course_ids, k_per_course=3)
        for d in docs:
            retrieved_chunks.append({
                "content": d.page_content,
                "file_name": d.metadata.get("file_name", ""),
                "course_id": d.metadata.get("course_id", ""),
            })

    if not retrieved_chunks:
        retrieved_chunks.append({"query": search_query})

    return {
        "messages": [HumanMessage(content=f"[课程检索] 关键词: {search_query}，找到 {len(retrieved_chunks)} 个相关片段")],
        "retrieved_chunks": retrieved_chunks,
    }


def rank_recommendations_node(state: RecommendState) -> dict[str, Any]:
    """Agent 3: Rank courses and generate recommendation rationale."""
    parsed = state["parsed_intent"]
    chunks = state.get("retrieved_chunks", [])
    course_ids = state.get("course_ids", [])
    candidate_courses = state.get("candidate_courses", [])

    context_parts = []
    for c in chunks:
        if isinstance(c, dict) and "content" in c:
            context_parts.append(c["content"])

    knowledge_context = "\n".join(context_parts[:5]) if context_parts else "无相关知识点片段。"

    # Build course list with metadata for the LLM
    course_descriptions = []
    for cc in candidate_courses:
        desc = (cc.get("description") or "")[:100]
        course_descriptions.append(
            f"ID {cc['id']}: 《{cc['title']}》 - {desc} [分类: {cc.get('category', '')}]"
        )
    course_list_str = "\n".join(course_descriptions) if course_descriptions else str(course_ids)

    llm = _llm()
    system_prompt = SystemMessage(
        content=(
            "你是一个AI学习路径规划师。根据用户的技能需求、目标和水平，"
            "从候选课程中推荐最合适的课程，并给出每门课的推荐理由。"
            "输出应为JSON数组，每个元素包含 course_id (int) 和 reason (str)。"
        )
    )
    user_msg = HumanMessage(
        content=(
            f"用户需求：{state['user_input']}\n"
            f"解析结果：{json.dumps(parsed, ensure_ascii=False)}\n"
            f"候选课程列表（ID、标题、简介、分类）：\n{course_list_str}\n"
            f"相关知识库片段：{knowledge_context}\n\n"
            "请根据课程标题、简介和知识库内容，推荐最适合用户需求的课程，并给出推荐理由。"
        )
    )
    try:
        response = llm.invoke([system_prompt, user_msg])
        text = response.content.strip() if isinstance(response.content, str) else str(response.content)
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        recommendations = json.loads(text)
        if isinstance(recommendations, list):
            return {"recommendations": recommendations}
    except Exception as exc:
        logger.warning("Recommendation ranking failed: %s", exc)

    # Fallback: return course IDs as-is without reason
    return {
        "recommendations": [{"course_id": cid, "reason": "热门推荐课程"} for cid in course_ids[:5]],
    }


def _build_recommend_graph() -> StateGraph:
    graph = StateGraph(RecommendState)
    graph.add_node("parse_intent", parse_intent_node)
    graph.add_node("retrieve_courses", retrieve_courses_node)
    graph.add_node("rank", rank_recommendations_node)

    graph.set_entry_point("parse_intent")
    graph.add_edge("parse_intent", "retrieve_courses")
    graph.add_edge("retrieve_courses", "rank")
    graph.add_edge("rank", END)
    return graph


# ═══════════════════════════════════════════════════════════════════
# ── 2. QUIZ GENERATION WORKFLOW ──
# ═══════════════════════════════════════════════════════════════════

class QuizQuestionOutput(BaseModel):
    """A single generated quiz question."""
    question: str = Field(description="题目内容")
    options: list[str] = Field(description="选择题选项（4个），问答题留空数组")
    answer: str = Field(description="正确答案（选择题如 'A'）或参考答案")


class QuizBatchOutput(BaseModel):
    """Batch of generated questions."""
    questions: list[QuizQuestionOutput] = Field(description="生成的题目列表")


class QuizState(TypedDict):
    course_id: int
    chapter_title: str
    knowledge_points: list[str]
    lesson_id: int | None
    question_types: list[str]
    difficulty: str
    count: int
    retrieved_content: list[str]
    questions: list[dict[str, Any]]
    validated_questions: list[dict[str, Any]]
    messages: list[BaseMessage]
    error: str | None


def retrieve_content_node(state: QuizState) -> dict[str, Any]:
    """Retrieve relevant content from the vector store."""
    query_parts = [state["chapter_title"]] + state.get("knowledge_points", [])
    query = " ".join(query_parts)
    docs = kb_manager.search_similar(query, course_id=state["course_id"], k=10)

    contents = []
    for d in docs:
        if d.page_content.strip():
            contents.append(d.page_content)

    return {
        "retrieved_content": contents,
        "messages": [HumanMessage(content=f"[内容检索] 检索到 {len(contents)} 个片段")],
    }


async def generate_questions_node(state: QuizState) -> dict[str, Any]:
    """Generate quiz questions based on retrieved content."""
    context = "\n---\n".join(state["retrieved_content"][:5])
    types_str = ", ".join(state.get("question_types", ["选择题", "问答题"]))
    chapter = state["chapter_title"]
    kps = ", ".join(state["knowledge_points"])

    if not context.strip():
        return {"questions": []}

    system_prompt = SystemMessage(
        content=(
            f"你是一个教育出题助手。请根据下方参考内容生成 {state['count']} 道{types_str}（难度：{state.get('difficulty', '中等')}）。\n"
            "选择题必须包含4个选项和正确答案（A/B/C/D）。问答题需包含参考答案。\n"
            "重要规则：\n"
            "1. 题目必须严格基于参考内容，禁止编造参考内容中没有的信息。\n"
            "2. 禁止出关于章节名称、编号、标题本身这类废话题。\n"
            "3. 题目应考察对参考内容中具体知识点的理解，而不是元信息。\n"
            "4. 如果参考内容不足以生成题目，返回空列表：{\"questions\": []}\n"
            "5. 题目之间不重复。\n\n"
            "必须输出严格的JSON格式（不要markdown，不要```，不要额外说明）：\n"
            '{"questions": [{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "A"}, ...]}'
        )
    )
    user_msg = HumanMessage(
        content=(
            f"课程章节：{chapter}\n"
            f"知识点：{kps}\n\n"
            f"参考内容：\n{context}\n\n"
            "只返回JSON，不要任何其他文字。"
        )
    )
    llm = _llm()
    try:
        resp = await llm.ainvoke([system_prompt, user_msg])
        # Try content first, then function call arguments
        text = ""
        if isinstance(resp.content, str) and resp.content.strip():
            text = resp.content.strip()
        elif hasattr(resp, "additional_kwargs"):
            if "function_call" in resp.additional_kwargs:
                text = resp.additional_kwargs["function_call"].get("arguments", "")
            elif "tool_calls" in resp.additional_kwargs:
                tc = resp.additional_kwargs["tool_calls"]
                if tc and isinstance(tc, list) and isinstance(tc[0], dict):
                    text = tc[0].get("function", {}).get("arguments", "")
        if not text:
            logger.info("LLM response empty, metadata=%s", getattr(resp, "response_metadata", {}))
            raise ValueError("empty LLM response")
        # Strip markdown code blocks and extract JSON
        text = text.strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if m:
                text = m.group(1).strip()
        # Extract the outermost JSON object only (handle extra content after closing brace)
        first_brace = text.find("{")
        if first_brace >= 0:
            depth, end = 0, first_brace
            for i in range(first_brace, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            text = text[first_brace:end]
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "questions" in parsed:
            questions = parsed["questions"]
        elif isinstance(parsed, list):
            questions = parsed
        else:
            raise ValueError(f"unexpected shape: {type(parsed)}")
    except Exception as exc:
        logger.warning("Quiz generation failed: %s", exc)
        questions = []

    return {"questions": questions}


def validate_questions_node(state: QuizState) -> dict[str, Any]:
    """Validate that questions are relevant and non-duplicate."""
    questions = state.get("questions", [])
    if len(questions) <= 1:
        return {"validated_questions": questions}

    system_prompt = SystemMessage(
        content="检查以下题目是否与课程内容相关且无重复。如有问题，请返回修正后的题目列表。"
    )
    user_msg = HumanMessage(content=json.dumps(questions, ensure_ascii=False))

    llm = _llm()
    try:
        response = llm.invoke([system_prompt, user_msg])
        text = response.content.strip() if isinstance(response.content, str) else str(response.content)
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        validated = json.loads(text)
        if isinstance(validated, list):
            return {"validated_questions": validated}
    except Exception:
        pass

    return {"validated_questions": questions}


def _build_quiz_graph() -> StateGraph:
    graph = StateGraph(QuizState)
    graph.add_node("retrieve_content", retrieve_content_node)
    graph.add_node("generate_questions", generate_questions_node)

    graph.set_entry_point("retrieve_content")
    graph.add_edge("retrieve_content", "generate_questions")
    graph.add_edge("generate_questions", END)
    return graph


# ═══════════════════════════════════════════════════════════════════
# ── 3. HOMEWORK GRADING WORKFLOW ──
# ═══════════════════════════════════════════════════════════════════

class GradeOutput(BaseModel):
    score: int = Field(ge=0, le=100, description="得分（0-100）")
    comment: str = Field(description="详细评语，包括正确点、错误点、改进建议")


class GradingState(TypedDict):
    question: str
    student_answer: str
    course_id: int | None
    reference_knowledge: list[str]
    score: int
    comment: str
    messages: list[BaseMessage]
    error: str | None


def retrieve_reference_node(state: GradingState) -> dict[str, Any]:
    """Retrieve reference knowledge for the question."""
    if state.get("course_id"):
        docs = kb_manager.search_similar(state["question"], course_id=state["course_id"], k=5)
        refs = [d.page_content for d in docs if d.page_content.strip()]
    else:
        refs = []

    if not refs:
        refs = ["无特定参考资料，请基于常识进行批改。"]

    return {
        "reference_knowledge": refs,
        "messages": [HumanMessage(content=f"[参考检索] 获取 {len(refs)} 个参考片段")],
    }


def grade_node(state: GradingState) -> dict[str, Any]:
    """Grade the student answer against the reference."""
    context = "\n---\n".join(state["reference_knowledge"][:3])

    system_prompt = SystemMessage(
        content=(
            "你是一个严格但友好的AI助教。请根据参考答案对学生答案进行批改：\n"
            "1. 指出回答正确的地方\n"
            "2. 指出错误或遗漏的地方\n"
            "3. 给出改进建议\n"
            "4. 给出0-100的分数"
        )
    )
    user_msg = HumanMessage(
        content=(
            f"题目：{state['question']}\n\n"
            f"学生答案：{state['student_answer']}\n\n"
            f"参考答案/知识点：\n{context}"
        )
    )

    llm = _llm().with_structured_output(GradeOutput, method="function_calling")
    try:
        result: GradeOutput = llm.invoke([system_prompt, user_msg])  # type: ignore[assignment]
        return {"score": result.score, "comment": result.comment}
    except Exception as exc:
        logger.warning("Grading failed, using fallback: %s", exc)
        return {"score": 60, "comment": "系统批改暂时不可用，请等待人工复核。"}


def _build_grading_graph() -> StateGraph:
    graph = StateGraph(GradingState)
    graph.add_node("retrieve_reference", retrieve_reference_node)
    graph.add_node("grade", grade_node)

    graph.set_entry_point("retrieve_reference")
    graph.add_edge("retrieve_reference", "grade")
    graph.add_edge("grade", END)
    return graph


# ═══════════════════════════════════════════════════════════════════
# Facade
# ═══════════════════════════════════════════════════════════════════

class LangGraphWorkflow:
    """Facade that exposes the three AI workflows.

    Each method compiles its graph on first call and caches it.
    """

    def __init__(self) -> None:
        self._recommend_graph: StateGraph | None = None
        self._quiz_graph: StateGraph | None = None
        self._grading_graph: StateGraph | None = None

    @property
    def recommend_graph(self):
        if self._recommend_graph is None:
            self._recommend_graph = _build_recommend_graph().compile()
        return self._recommend_graph

    @property
    def quiz_graph(self):
        if self._quiz_graph is None:
            self._quiz_graph = _build_quiz_graph().compile()
        return self._quiz_graph

    @property
    def grading_graph(self):
        if self._grading_graph is None:
            self._grading_graph = _build_grading_graph().compile()
        return self._grading_graph

    async def run_recommend(
        self,
        user_input: str,
        course_ids: list[int] | None = None,
        candidate_courses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run the course recommendation workflow.

        Args:
            user_input: The user's learning needs description.
            course_ids: Candidate course IDs to recommend from.
            candidate_courses: Full metadata (id, title, description, category) of candidates.

        Returns:
            ``{"recommendations": [...], "parsed_intent": {...}}``
        """
        initial: RecommendState = {
            "user_input": user_input,
            "parsed_intent": {},
            "course_ids": course_ids or [],
            "candidate_courses": candidate_courses or [],
            "retrieved_chunks": [],
            "recommendations": [],
            "messages": [],
            "error": None,
        }
        result = await self.recommend_graph.ainvoke(initial)
        return {
            "recommendations": result.get("recommendations", []),
            "parsed_intent": result.get("parsed_intent", {}),
        }

    async def run_quiz_generation(
        self,
        course_id: int,
        chapter_title: str,
        knowledge_points: list[str],
        lesson_id: int | None = None,
        question_types: list[str] | None = None,
        difficulty: str = "中等",
        count: int = 5,
    ) -> dict[str, Any]:
        """Run the quiz generation workflow.

        Returns:
            ``{"questions": [...], "mock": false}``
        """
        initial: QuizState = {
            "course_id": course_id,
            "chapter_title": chapter_title,
            "knowledge_points": knowledge_points,
            "lesson_id": lesson_id,
            "question_types": question_types or ["选择题", "问答题"],
            "difficulty": difficulty,
            "count": count,
            "retrieved_content": [],
            "questions": [],
            "validated_questions": [],
            "messages": [],
            "error": None,
        }
        result = await self.quiz_graph.ainvoke(initial)
        questions = result.get("questions", [])
        return {"questions": questions, "mock": False}

    async def run_grading(
        self,
        question: str,
        student_answer: str,
        course_id: int | None = None,
    ) -> dict[str, Any]:
        """Run the homework grading workflow.

        Returns:
            ``{"score": int, "comment": str, "mock": false}``
        """
        initial: GradingState = {
            "question": question,
            "student_answer": student_answer,
            "course_id": course_id,
            "reference_knowledge": [],
            "score": 0,
            "comment": "",
            "messages": [],
            "error": None,
        }
        result = await self.grading_graph.ainvoke(initial)
        return {
            "score": result.get("score", 0),
            "comment": result.get("comment", ""),
            "mock": False,
        }


# Singleton
workflow = LangGraphWorkflow()
