from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.diary_entry import DiaryEntry
from app.models.user import User
from app.schemas.diary_entry import (
    DiaryEntryBulkDelete,
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
)
from app.services.diary_entry_service import DiaryEntryService

router = APIRouter(prefix="/diary-entries", tags=["diary"])


@router.get("", response_model=list[DiaryEntryResponse])
async def list_diary_entries(
    pet_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DiaryEntry]:
    return await DiaryEntryService(db).get_entries(current_user.id, pet_id)


@router.post("", response_model=DiaryEntryResponse, status_code=201)
async def create_diary_entry(
    data: DiaryEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiaryEntry:
    return await DiaryEntryService(db).create_entry(current_user.id, data)


@router.post("/bulk-delete", status_code=204)
async def bulk_delete_diary_entries(
    data: DiaryEntryBulkDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await DiaryEntryService(db).delete_entries(data.ids, current_user.id)


@router.get("/{entry_id}", response_model=DiaryEntryResponse)
async def get_diary_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiaryEntry:
    return await DiaryEntryService(db).get_entry(entry_id, current_user.id)


@router.patch("/{entry_id}", response_model=DiaryEntryResponse)
async def update_diary_entry(
    entry_id: int,
    data: DiaryEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiaryEntry:
    return await DiaryEntryService(db).update_entry(entry_id, current_user.id, data)


@router.delete("/{entry_id}", status_code=204)
async def delete_diary_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await DiaryEntryService(db).delete_entry(entry_id, current_user.id)
