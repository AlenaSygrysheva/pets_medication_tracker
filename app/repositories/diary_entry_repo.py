from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diary_entry import DiaryEntry
from app.models.pet import Pet
from app.schemas.diary_entry import DiaryEntryCreate, DiaryEntryUpdate


class DiaryEntryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, entry_id: int) -> DiaryEntry | None:
        result = await self.db.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int, pet_id: int | None = None) -> list[DiaryEntry]:
        q = select(DiaryEntry).join(Pet, DiaryEntry.pet_id == Pet.id).where(Pet.owner_id == owner_id)
        if pet_id is not None:
            q = q.where(DiaryEntry.pet_id == pet_id)
        # id breaks ties between entries created within the same second.
        result = await self.db.execute(q.order_by(DiaryEntry.created_at.desc(), DiaryEntry.id.desc()))
        return list(result.scalars().all())

    async def get_owned_ids(self, owner_id: int, ids: list[int]) -> set[int]:
        result = await self.db.execute(
            select(DiaryEntry.id)
            .join(Pet, DiaryEntry.pet_id == Pet.id)
            .where(Pet.owner_id == owner_id, DiaryEntry.id.in_(ids))
        )
        return set(result.scalars().all())

    async def create(self, data: DiaryEntryCreate) -> DiaryEntry:
        entry = DiaryEntry(**data.model_dump())
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def update(self, entry: DiaryEntry, data: DiaryEntryUpdate) -> DiaryEntry:
        entry.text = data.text
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def delete(self, entry: DiaryEntry) -> None:
        await self.db.delete(entry)
        await self.db.flush()

    async def delete_many(self, ids: list[int]) -> None:
        await self.db.execute(delete(DiaryEntry).where(DiaryEntry.id.in_(ids)))
        await self.db.flush()
