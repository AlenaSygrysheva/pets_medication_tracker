from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnosis import Diagnosis
from app.models.pet import Pet
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisUpdate


class DiagnosisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, diagnosis_id: int) -> Diagnosis | None:
        result = await self.db.execute(select(Diagnosis).where(Diagnosis.id == diagnosis_id))
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int, pet_id: int | None = None) -> list[Diagnosis]:
        q = select(Diagnosis).join(Pet, Diagnosis.pet_id == Pet.id).where(Pet.owner_id == owner_id)
        if pet_id is not None:
            q = q.where(Diagnosis.pet_id == pet_id)
        result = await self.db.execute(q.order_by(Diagnosis.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, data: DiagnosisCreate) -> Diagnosis:
        diagnosis = Diagnosis(**data.model_dump())
        self.db.add(diagnosis)
        await self.db.flush()
        await self.db.refresh(diagnosis)
        return diagnosis

    async def update(self, diagnosis: Diagnosis, data: DiagnosisUpdate) -> Diagnosis:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(diagnosis, field, value)
        await self.db.flush()
        await self.db.refresh(diagnosis)
        return diagnosis

    async def delete(self, diagnosis: Diagnosis) -> None:
        await self.db.delete(diagnosis)
        await self.db.flush()
