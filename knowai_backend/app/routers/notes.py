from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth import get_current_user
from app.crud import notes_crud
from app.database import get_mongo
from app.models import User
from app.schemas import NoteCreate, NoteRead, NoteUpdate

router = APIRouter()


@router.get("", response_model=list[NoteRead])
async def list_notes(
    mongo: Annotated[AsyncIOMotorDatabase, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
    course_id: Annotated[int, Query(ge=1)],
    lesson_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[NoteRead]:
    items = await notes_crud.list_course_notes(mongo, current_user.id, course_id, lesson_id)
    return [
        NoteRead(
            id=item["_id"],
            lesson_id=item["lesson_id"],
            course_id=item["course_id"],
            content=item["content"],
            timestamp=item.get("timestamp", 0),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in items
    ]


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    mongo: Annotated[AsyncIOMotorDatabase, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    doc = await notes_crud.create_note(
        mongo, current_user.id, payload.lesson_id, payload.course_id, payload.content, payload.timestamp
    )
    return NoteRead(
        id=doc["_id"],
        lesson_id=doc["lesson_id"],
        course_id=doc["course_id"],
        content=doc["content"],
        timestamp=doc.get("timestamp", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.put("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    mongo: Annotated[AsyncIOMotorDatabase, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    doc = await notes_crud.update_note(mongo, note_id, current_user.id, payload.content, payload.timestamp)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
    return NoteRead(
        id=doc["_id"],
        lesson_id=doc["lesson_id"],
        course_id=doc["course_id"],
        content=doc["content"],
        timestamp=doc.get("timestamp", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    mongo: Annotated[AsyncIOMotorDatabase, Depends(get_mongo)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await notes_crud.delete_note(mongo, note_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
