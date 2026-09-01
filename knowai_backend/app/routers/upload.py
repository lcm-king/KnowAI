import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.auth import get_current_user
from app.config import settings
from app.models import User, UserRole
from app.schemas import UploadResponse

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/x-msvideo"}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Extension whitelist (lowercase, no dot) - defence in depth, since content_type can be forged
ALLOWED_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_VIDEO_EXTS = {"mp4", "webm", "avi"}
ALLOWED_DOCUMENT_EXTS = {"pdf", "txt", "md", "markdown", "doc", "docx"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB


async def get_teacher_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in (UserRole.admin, UserRole.teacher):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要讲师或管理员权限")
    return current_user


def _ensure_upload_subdir(subdir: str) -> Path:
    path = settings.upload_dir / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_ext(filename: str | None) -> str | None:
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[-1].lower()


def _save_upload(file: UploadFile, content: bytes, subdir: str, allowed_exts: set[str]) -> str:
    ext = _extract_ext(file.filename)
    if ext is None or ext not in allowed_exts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不允许的文件扩展名，仅支持: {', '.join(sorted(allowed_exts))}")
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_dir = _ensure_upload_subdir(subdir)
    (save_dir / filename).write_bytes(content)
    return f"{settings.api_prefix}/uploads/{subdir}/{filename}"


@router.post("/cover", response_model=UploadResponse)
async def upload_cover(
    user: Annotated[User, Depends(get_teacher_or_admin)],
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload a course cover image (teacher or admin only)."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的图片格式，仅支持 JPEG/PNG/GIF/WebP")
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片大小超过 5MB 限制")
    url = _save_upload(file, content, "covers", ALLOWED_IMAGE_EXTS)
    return UploadResponse(url=url, filename=file.filename or "image", size=len(content))


@router.post("/video", response_model=UploadResponse)
async def upload_video(
    user: Annotated[User, Depends(get_teacher_or_admin)],
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload a lesson video (teacher or admin only)."""
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的视频格式，仅支持 MP4/WebM/AVI")
    content = await file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="视频大小超过 200MB 限制")
    url = _save_upload(file, content, "videos", ALLOWED_VIDEO_EXTS)
    return UploadResponse(url=url, filename=file.filename or "video", size=len(content))


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    user: Annotated[User, Depends(get_teacher_or_admin)],
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload a knowledge document (teacher or admin only)."""
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文档格式，仅支持 PDF/TXT/Markdown/DOC")
    content = await file.read()
    if len(content) > MAX_DOCUMENT_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档大小超过 50MB 限制")
    url = _save_upload(file, content, "documents", ALLOWED_DOCUMENT_EXTS)
    return UploadResponse(url=url, filename=file.filename or "document", size=len(content))
