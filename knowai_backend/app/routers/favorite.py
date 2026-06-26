from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import favorite_crud
from app.database import get_db
from app.models import Course, User
from app.schemas import CourseDetailListResponse, CourseDetailRead

router = APIRouter()


async def _course_to_read(db: AsyncSession, course: Course) -> CourseDetailRead:
    item = CourseDetailRead.model_validate(course)
    return item


@router.get("")
async def list_favorites(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CourseDetailListResponse:
    total, courses = await favorite_crud.list_user_favorites(db, current_user, page, page_size)
    return CourseDetailListResponse(total=total, items=[await _course_to_read(db, c) for c in courses])


@router.post("/{course_id}")
async def toggle_favorite(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    favorited = await favorite_crud.toggle_favorite(db, current_user, course_id)
    return {"favorited": favorited, "message": "已收藏" if favorited else "已取消收藏"}


@router.get("/check/{course_id}")
async def check_favorite(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    is_fav = await favorite_crud.is_favorited(db, current_user, course_id)
    return {"favorited": is_fav}
