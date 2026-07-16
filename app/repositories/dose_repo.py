from datetime import date, datetime

from sqlalchemy import and_, delete, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication


class DoseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, dose_id: int) -> Dose | None:
        result = await self.db.execute(
            select(Dose).where(Dose.id == dose_id).options(selectinload(Dose.medication))
        )
        return result.scalar_one_or_none()

    async def get_doses_for_pet_day(self, pet_id: int, day: date) -> list[Dose]:
        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        result = await self.db.execute(
            select(Dose)
            .join(Medication)
            .where(
                and_(
                    Medication.pet_id == pet_id,
                    Dose.scheduled_at >= start,
                    Dose.scheduled_at <= end,
                )
            )
            .options(selectinload(Dose.medication))
            .order_by(Dose.scheduled_at)
        )
        return list(result.scalars().all())

    async def create_bulk(self, doses: list[Dose]) -> None:
        self.db.add_all(doses)
        await self.db.flush()

    async def update_status(
        self,
        dose: Dose,
        status: DoseStatus,
        taken_at: datetime | None = None,
        notes: str | None = None,
    ) -> Dose:
        dose.status = status
        if taken_at:
            dose.taken_at = taken_at
        if notes is not None:
            dose.notes = notes
        await self.db.flush()
        await self.db.refresh(dose)
        return dose

    async def delete_pending_for_medication(self, medication_id: int) -> None:
        await self.db.execute(
            delete(Dose).where(
                and_(Dose.medication_id == medication_id, Dose.status == DoseStatus.PENDING)
            )
        )
        await self.db.flush()

    async def cancel_pending_doses(self, medication_id: int) -> int:
        result = await self.db.execute(
            sa_update(Dose)
            .where(and_(Dose.medication_id == medication_id, Dose.status == DoseStatus.PENDING))
            .values(status=DoseStatus.CANCELLED)
            .returning(Dose.id)
        )
        await self.db.flush()
        return len(result.fetchall())

    async def get_overdue_pending(self, before: datetime) -> list[Dose]:
        result = await self.db.execute(
            select(Dose).where(
                and_(Dose.status == DoseStatus.PENDING, Dose.scheduled_at < before)
            )
        )
        return list(result.scalars().all())
