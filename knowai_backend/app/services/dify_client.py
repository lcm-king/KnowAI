import json
from typing import Any

import httpx

from app.config import settings

MOCK_QUIZ = [
    {
        "question": "人工智能的核心目标是什么？",
        "options": ["模拟和扩展人类智能", "替代所有软件", "只处理表格数据", "只用于图像压缩"],
        "answer": "A",
    }
]
MOCK_RECOMMEND_COURSE_IDS = [1, 2, 3]
MOCK_HOMEWORK_GRADE = {"score": 88, "comment": "答案覆盖了主要知识点，建议补充关键概念的应用场景。"}


class DifyClient:
    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.api_key != "app-xxxxxxxx")

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any], user: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Dify API key is not configured")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.api_url}/workflows/{workflow_id}/run",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"inputs": inputs, "response_mode": "blocking", "user": user},
            )
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data") or {}
        if data.get("status") != "succeeded":
            raise RuntimeError(data.get("error") or "Dify workflow failed")
        return data.get("outputs") or {}


client = DifyClient(settings.dify_api_url, settings.dify_api_key)


def parse_json_output(outputs: dict[str, Any], default: Any) -> Any:
    for key in ("result", "text", "answer", "output", "outputs"):
        value = outputs.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                continue
        return value
    return default


async def generate_quiz(inputs: dict[str, Any], user: str) -> tuple[list[dict[str, Any]], bool]:
    try:
        outputs = await client.run_workflow("quiz_generation", inputs, user)
        return parse_json_output(outputs, MOCK_QUIZ), False
    except Exception:
        return MOCK_QUIZ, True


async def recommend_courses(inputs: dict[str, Any], user: str) -> tuple[list[int], bool]:
    try:
        outputs = await client.run_workflow("course_recommend", inputs, user)
        course_ids = parse_json_output(outputs, MOCK_RECOMMEND_COURSE_IDS)
        return [int(course_id) for course_id in course_ids], False
    except Exception:
        return MOCK_RECOMMEND_COURSE_IDS, True


async def grade_homework(inputs: dict[str, Any], user: str) -> tuple[dict[str, Any], bool]:
    try:
        outputs = await client.run_workflow("homework_grading", inputs, user)
        return parse_json_output(outputs, MOCK_HOMEWORK_GRADE), False
    except Exception:
        return MOCK_HOMEWORK_GRADE, True


MOCK_CHAT_REPLIES = [
    "好的，我来帮你梳理一下这个知识点的学习路径：先掌握基础概念，再通过实战项目巩固。",
    "根据你的提问，建议你回顾课程中的相关章节，并结合练习题加深理解。",
    "这是一个很好的问题。可以尝试从定义出发，再结合例子去推理。",
    "学习的关键在于持续练习。建议你每天专注 30 分钟，循序渐进。",
]


async def chat_with_assistant(message: str, user: str) -> tuple[str, bool]:
    try:
        outputs = await client.run_workflow(
            "chat_assistant",
            {"message": message},
            user,
        )
        text = outputs.get("answer") or outputs.get("text") or outputs.get("output")
        if isinstance(text, str) and text.strip():
            return text, False
        if isinstance(text, dict):
            return str(text.get("content") or text), False
    except Exception:
        pass
    index = (len(message) * 7) % len(MOCK_CHAT_REPLIES)
    return MOCK_CHAT_REPLIES[index], True
