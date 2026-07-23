
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.schemas.medication import MedicationCreate, MedicationUpdate


class MedicationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, medication_id: int) -> Medication | None:
        result = await self.db.execute(select(Medication).where(Medication.id == medication_id))
        return result.scalar_one_or_none()

    async def get_all_by_pet(self, pet_id: int, active_only: bool = False) -> list[Medication]:
        q = select(Medication).where(Medication.pet_id == pet_id, Medication.is_deleted.is_(False))
        if active_only:
            q = q.where(Medication.is_active.is_(True))
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_ended_by_pet(self, pet_id: int) -> list[Medication]:
        """Medications whose course has ended — either cancelled, or with no pending
        doses left (a missed/skipped dose keeps getting replaced further down the
        schedule, so "past end_date" alone does not mean the course is done)."""
        has_pending = (
            select(Dose.id)
            .where(Dose.medication_id == Medication.id, Dose.status == DoseStatus.PENDING)
            .exists()
        )
        result = await self.db.execute(
            select(Medication).where(
                Medication.pet_id == pet_id,
                Medication.is_deleted.is_(False),
                or_(Medication.is_active.is_(False), ~has_pending),
            )
        )
        return list(result.scalars().all())

    async def create(self, data: MedicationCreate) -> Medication:
        medication = Medication(**data.model_dump())
        self.db.add(medication)
        await self.db.flush()
        await self.db.refresh(medication)
        return medication

    async def update(self, medication: Medication, data: MedicationUpdate) -> Medication:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(medication, field, value)
        await self.db.flush()
        await self.db.refresh(medication)
        return medication

    async def soft_delete(self, medication: Medication) -> None:
        medication.is_deleted = True
        medication.is_active = False
        await self.db.flush()
