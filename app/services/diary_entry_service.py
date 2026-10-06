from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.diary_entry import DiaryEntry
from app.repositories.diary_entry_repo import DiaryEntryRepository
from app.repositories.pet_repo import PetRepository
from app.schemas.diary_entry import DiaryEntryCreate, DiaryEntryUpdate


class DiaryEntryService:
    def __init__(self, db: AsyncSession):
        self.repo = DiaryEntryRepository(db)
        self.pet_repo = PetRepository(db)

    async def _validate_pet(self, pet_id: int, owner_id: int) -> None:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

    async def get_entries(self, owner_id: int, pet_id: int | None = None) -> list[DiaryEntry]:
        if pet_id is not None:
            await self._validate_pet(pet_id, owner_id)
        return await self.repo.get_all_by_owner(owner_id, pet_id)

    async def get_entry(self, entry_id: int, owner_id: int) -> DiaryEntry:
        entry = await self.repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError("Diary entry not found")
        await self._validate_pet(entry.pet_id, owner_id)
        return entry

    async def create_entry(self, owner_id: int, data: DiaryEntryCreate) -> DiaryEntry:
        await self._validate_pet(data.pet_id, owner_id)
        return await self.repo.create(data)

    async def update_entry(self, entry_id: int, owner_id: int, data: DiaryEntryUpdate) -> DiaryEntry:
        entry = await self.get_entry(entry_id, owner_id)
        return await self.repo.update(entry, data)

    async def delete_entry(self, entry_id: int, owner_id: int) -> None:
        entry = await self.get_entry(entry_id, owner_id)
        await self.repo.delete(entry)

    async def delete_entries(self, ids: list[int], owner_id: int) -> None:
        """All-or-nothing: if any id is missing or belongs to someone else,
        nothing is deleted."""
        unique_ids = list(set(ids))
        owned = await self.repo.get_owned_ids(owner_id, unique_ids)
        if len(owned) != len(unique_ids):
            raise NotFoundError("Diary entry not found")
        await self.repo.delete_many(unique_ids)
