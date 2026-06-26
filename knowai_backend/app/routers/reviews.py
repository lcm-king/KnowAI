from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Course, CourseStatus, CourseReview, User
from app.schemas import ReviewCreate, ReviewListResponse, ReviewRead, ReviewUpdate

router = APIRouter()


async def get_course_review_or_404(db: AsyncSession, review_id: int) -> CourseReview:
    from app.crud.review_crud import get_review

    review = await get_review(db, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评价不存在")
    return review


@router.post("/{course_id}/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_course_review(
    course_id: int,
    review_in: ReviewCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewRead:
    """Create a review for a course (one per user per course)."""
    from app.crud.review_crud import create_review, get_user_course_review

    # Verify course exists and is published
    course = await db.get(Course, course_id)
    if course is None or course.status != CourseStatus.published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    # Check for duplicate review
    existing = await get_user_course_review(db, course_id, current_user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="您已经评价过该课程",
        )

    review = await create_review(db, course_id, current_user.id, review_in)
    await db.commit()
    review_read = ReviewRead.model_validate(review)
    review_read.username = current_user.username
    return review_read


@router.get("/{course_id}/reviews", response_model=ReviewListResponse)
async def list_course_reviews(
    course_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReviewListResponse:
    """List all reviews for a course (public)."""
    from app.crud.review_crud import list_course_reviews

    # Verify course exists
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    total, reviews = await list_course_reviews(db, course_id, page, page_size)
    items = []
    for r in reviews:
        item = ReviewRead.model_validate(r)
        item.username = r.user.username if r.user else None
        items.append(item)

    return ReviewListResponse(
        total=total,
        items=items,
        average_rating=course.rating,
        review_count=total,
    )


@router.put("/{course_id}/reviews/{review_id}", response_model=ReviewRead)
async def update_course_review(
    course_id: int,
    review_id: int,
    review_in: ReviewUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewRead:
    """Update own review for a course."""
    from app.crud.review_crud import update_review

    review = await get_course_review_or_404(db, review_id)
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该评价")
    if review.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评价不属于该课程")

    review = await update_review(db, review, review_in)
    await db.commit()
    review_read = ReviewRead.model_validate(review)
    review_read.username = current_user.username
    return review_read


@router.delete("/{course_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_review(
    course_id: int,
    review_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete own review."""
    from app.crud.review_crud import delete_review

    review = await get_course_review_or_404(db, review_id)
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该评价")
    if review.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评价不属于该课程")

    await delete_review(db, review)
    await db.commit()
