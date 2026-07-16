
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import Pet
from app.schemas.pet import PetCreate, PetUpdate


class PetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, pet_id: int) -> Pet | None:
        result = await self.db.execute(select(Pet).where(Pet.id == pet_id))
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int) -> list[Pet]:
        result = await self.db.execute(select(Pet).where(Pet.owner_id == owner_id))
        return list(result.scalars().all())

    async def create(self, owner_id: int, data: PetCreate) -> Pet:
        pet = Pet(owner_id=owner_id, **data.model_dump())
        self.db.add(pet)
        await self.db.flush()
        await self.db.refresh(pet)
        return pet

    async def update(self, pet: Pet, data: PetUpdate) -> Pet:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(pet, field, value)
        await self.db.flush()
        await self.db.refresh(pet)
        return pet

    async def update_avatar(self, pet: Pet, avatar_path: str) -> Pet:
        pet.avatar_path = avatar_path
        await self.db.flush()
        await self.db.refresh(pet)
        return pet

    async def delete(self, pet: Pet) -> None:
        await self.db.delete(pet)
        await self.db.flush()
