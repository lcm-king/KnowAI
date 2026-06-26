"""
Knowledge Base Management
- Document loading & chunking (RecursiveCharacterTextSplitter)
- Vector embedding & storage (Chroma + custom HTTP embedding)
- Incremental index refresh per course/lesson
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
import httpx
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger("knowai.knowledge_base")


# ── Custom embedding function (no tiktoken dependency) ─────────────

class HttpEmbeddings:
    """Minimal embedding class that calls an OpenAI-compatible API via HTTP.

    Avoids the tiktoken dependency that ``OpenAIEmbeddings`` requires
    (the encoding file download is blocked on some networks).
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Call the embedding API and return vectors."""
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            # Sort by index to preserve order
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class KnowledgeBaseManager:
    """Manages vector index for course/lesson knowledge files.

    Each course gets a Chroma collection named ``course_{course_id}``.
    Lesson-level files are included in the same course collection with
    ``lesson_id`` metadata so queries can filter by course or lesson.

    Initialization is lazy — the OpenAI client is created on first use,
    allowing the module to be imported even when no API key is configured.
    """

    def __init__(self) -> None:
        self.persist_dir = Path(settings.vector_db_path)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._embeddings = None
        self._chroma_client = None

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
            length_function=len,
        )

    @property
    def embeddings(self):
        if self._embeddings is None:
            api_key = settings.embedding_api_key or settings.openai_api_key
            base_url = settings.embedding_base_url or "https://api.siliconflow.cn/v1"
            if not api_key:
                raise RuntimeError(
                    "Embedding API key is not configured. "
                    "Set EMBEDDING_API_KEY or OPENAI_API_KEY in .env."
                )
            self._embeddings = HttpEmbeddings(
                model=settings.embedding_model,
                api_key=api_key,
                base_url=base_url,
            )
        return self._embeddings

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir / "chroma_db"),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._chroma_client

    # ── collection helpers ────────────────────────────────────────

    def _collection_name(self, course_id: int) -> str:
        return f"course_{course_id}"

    def _get_or_create_collection(self, course_id: int) -> Chroma:
        return Chroma(
            client=self.chroma_client,
            collection_name=self._collection_name(course_id),
            embedding_function=self.embeddings,
        )

    def _delete_collection(self, course_id: int) -> None:
        try:
            self.chroma_client.delete_collection(self._collection_name(course_id))
        except ValueError:
            pass  # collection does not exist

    # ── file loading ──────────────────────────────────────────────

    def _load_text_from_file(self, file_path: str, file_type: str) -> str | None:
        """Read text content from a file on disk.

        Supports TXT, MD (via TextLoader) and PDF (via PyPDFLoader).
        Returns ``None`` if the file cannot be read.
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("File not found on disk: %s", file_path)
            return None

        try:
            if file_type in ("text/plain", "text/markdown", "text/plain; charset=utf-8"):
                loader = TextLoader(str(path), encoding="utf-8")
            elif file_type == "application/pdf":
                loader = PyPDFLoader(str(path))
            else:
                # DOCX – try docx2txt (fallback: skip)
                try:
                    import docx2txt  # noqa: F811
                    text = docx2txt.process(str(path))
                    return text if text.strip() else None
                except ImportError:
                    logger.warning("docx2txt not installed, skipping DOCX: %s", file_path)
                    return None

            docs = loader.load()
            return "\n".join(d.page_content for d in docs if d.page_content.strip())

        except Exception as exc:
            logger.error("Failed to load file %s: %s", file_path, exc)
            return None

    # ── index building ────────────────────────────────────────────

    def build_course_index(
        self,
        course_id: int,
        files: list[dict[str, Any]],
    ) -> int:
        """Build / rebuild the vector index for a course's knowledge files.

        ``files`` is a list of dicts with keys:
            id, file_name, file_url, file_type, file_size, content (str | None)

        Returns the total number of chunks indexed.
        """
        self._delete_collection(course_id)
        vector_store = self._get_or_create_collection(course_id)

        documents: list[Document] = []
        for f in files:
            text = (f.get("content") or "").strip()
            if not text:
                # Try loading from disk
                file_url: str = f.get("file_url", "")
                if file_url.startswith(settings.api_prefix + "/uploads/"):
                    rel = file_url[len(settings.api_prefix + "/uploads/"):]
                    disk_path = str(settings.upload_dir / rel)
                    text = self._load_text_from_file(disk_path, f.get("file_type", "")) or ""

            if not text:
                logger.info("Skipping empty file: %s", f.get("file_name"))
                continue

            chunks = self.text_splitter.split_text(text)
            for chunk in chunks:
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "course_id": str(course_id),
                        "file_id": str(f["id"]),
                        "file_name": f.get("file_name", ""),
                        "file_type": f.get("file_type", ""),
                        "lesson_id": f.get("lesson_id", "0"),
                    },
                )
                documents.append(doc)

        if documents:
            vector_store.add_documents(documents)
            logger.info(
                "Indexed course %s: %d chunks from %d files",
                course_id, len(documents), len(files),
            )
        return len(documents)

    def build_lesson_index(
        self,
        course_id: int,
        lesson_id: int,
        files: list[dict[str, Any]],
    ) -> int:
        """Index lesson-level files into the course collection."""
        return self.build_course_index(course_id, files)

    # ── search ───────────────────────────────────────────────────

    def search_similar(
        self,
        query: str,
        course_id: int | None = None,
        lesson_id: int | None = None,
        k: int = 5,
    ) -> list[Document]:
        """Search for similar content across the specified vector index.

        Returns up to ``k`` documents.
        """
        if course_id is None:
            return []

        vector_store = self._get_or_create_collection(course_id)
        filter_expr: dict[str, Any] = {}
        if lesson_id:
            filter_expr["lesson_id"] = str(lesson_id)

        try:
            results = vector_store.similarity_search(query, k=k, filter=filter_expr)
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []

        return results

    def search_all_courses(
        self,
        query: str,
        course_ids: list[int],
        k_per_course: int = 3,
    ) -> list[Document]:
        """Search across multiple course collections."""
        all_docs: list[Document] = []
        for cid in course_ids:
            docs = self.search_similar(query, course_id=cid, k=k_per_course)
            all_docs.extend(docs)
        return all_docs

    # ── deletion ──────────────────────────────────────────────────

    def delete_course_index(self, course_id: int) -> None:
        """Remove the entire vector index for a course."""
        self._delete_collection(course_id)
        logger.info("Deleted vector index for course %s", course_id)

    def delete_lesson_index(self, course_id: int, lesson_id: int) -> None:
        """Remove lesson-level entries from the course collection.

        Chroma does not support per-document deletion easily via langchain,
        so we rebuild the index excluding the deleted lesson's files.
        For simplicity this is a no-op; the full rebuild via
        ``refresh_course_knowledge`` handles it.
        """
        logger.info(
            "Deletion of lesson %s index deferred to next course rebuild",
            lesson_id,
        )


# Module-level singleton
kb_manager = KnowledgeBaseManager()


# ── async helper used by routers ─────────────────────────────────

async def refresh_course_knowledge(course_id: int, db: AsyncSession) -> int:
    """Rebuild the vector index for a course from its knowledge files.

    Called as a background task when files are added / removed.
    Returns total chunk count.
    """
    from app.models import Chapter, CourseKnowledge, KnowledgeVector, Lesson, LessonKnowledge

    # Collect all course-level knowledge files
    result = await db.execute(
        select(CourseKnowledge).where(CourseKnowledge.course_id == course_id)
    )
    course_knowledge = list(result.scalars().all())

    # Collect all lesson-level knowledge files for lessons of this course
    result = await db.execute(
        select(LessonKnowledge)
        .join(Lesson, LessonKnowledge.lesson_id == Lesson.id)
        .join(Chapter, Lesson.chapter_id == Chapter.id)
        .where(Chapter.course_id == course_id)
    )
    lesson_knowledge = list(result.scalars().all())

    files: list[dict[str, Any]] = []
    file_ids: list[int] = []

    for ck in course_knowledge:
        files.append({
            "id": ck.id,
            "file_name": ck.file_name,
            "file_url": ck.file_url,
            "file_type": ck.file_type,
            "file_size": ck.file_size,
            "content": ck.content,
            "lesson_id": 0,
        })
        file_ids.append(ck.id)

    for lk in lesson_knowledge:
        files.append({
            "id": lk.id,
            "file_name": lk.file_name,
            "file_url": lk.file_url,
            "file_type": lk.file_type,
            "file_size": lk.file_size,
            "content": lk.content,
            "lesson_id": lk.lesson_id,
        })
        file_ids.append(lk.id)

    if not files:
        kb_manager.delete_course_index(course_id)
        return 0

    # Clear old vector metadata
    await db.execute(
        select(KnowledgeVector).where(KnowledgeVector.course_id == course_id)
    )
    # Build index
    chunk_count = kb_manager.build_course_index(course_id, files)

    # Upsert metadata
    from sqlalchemy.dialects.mysql import insert as mysql_insert

    insert_stmt = mysql_insert(KnowledgeVector).values(
        course_id=course_id,
        file_id=hash(tuple(file_ids)) & 0x7FFFFFFF,  # deterministic surrogate key
        file_type="course",
        chunk_count=chunk_count,
        vector_store_id=kb_manager._collection_name(course_id),
    )
    on_duplicate = insert_stmt.on_duplicate_key_update(
        chunk_count=chunk_count,
        updated_at=KnowledgeVector.updated_at,  # triggers server default / onupdate
    )
    await db.execute(on_duplicate)
    await db.commit()

    logger.info("Refreshed knowledge index for course %s: %d chunks", course_id, chunk_count)
    return chunk_count
