from datetime import UTC, date, datetime, time

from sqlalchemy import and_, delete, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.models.pet import Pet


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

    async def cancel_pending_up_to(self, medication_id: int, as_of: date) -> int:
        """Mark pending doses scheduled on or before `as_of` as cancelled (kept for history)."""
        cutoff = datetime.combine(as_of, time.max, tzinfo=UTC)
        result = await self.db.execute(
            sa_update(Dose)
            .where(
                and_(
                    Dose.medication_id == medication_id,
                    Dose.status == DoseStatus.PENDING,
                    Dose.scheduled_at <= cutoff,
                )
            )
            .values(status=DoseStatus.CANCELLED)
            .returning(Dose.id)
        )
        await self.db.flush()
        return len(result.fetchall())

    async def delete_pending_after(self, medication_id: int, as_of: date) -> int:
        """Erase pending doses scheduled strictly after `as_of` — they will never happen."""
        cutoff = datetime.combine(as_of, time.max, tzinfo=UTC)
        result = await self.db.execute(
            delete(Dose)
            .where(
                and_(
                    Dose.medication_id == medication_id,
                    Dose.status == DoseStatus.PENDING,
                    Dose.scheduled_at > cutoff,
                )
            )
            .returning(Dose.id)
        )
        await self.db.flush()
        return len(result.fetchall())

    async def get_last_scheduled(self, medication_id: int) -> Dose | None:
        result = await self.db.execute(
            select(Dose)
            .where(Dose.medication_id == medication_id)
            .order_by(Dose.scheduled_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_status_counts(self, medication_id: int) -> dict[str, int]:
        result = await self.db.execute(
            select(Dose.status, func.count(Dose.id))
            .where(Dose.medication_id == medication_id)
            .group_by(Dose.status)
        )
        return {status.value: count for status, count in result.all()}

    async def get_overdue_pending(self, before: datetime) -> list[Dose]:
        result = await self.db.execute(
            select(Dose)
            .where(and_(Dose.status == DoseStatus.PENDING, Dose.scheduled_at < before))
            .options(selectinload(Dose.medication))
        )
        return list(result.scalars().all())

    async def get_month_doses(
        self, owner_id: int, start: date, end: date
    ) -> list[tuple[datetime, int, str]]:
        """(scheduled_at, pet_id, pet_name) for every dose in range across all of the owner's pets."""
        start_dt = datetime.combine(start, time.min, tzinfo=UTC)
        end_dt = datetime.combine(end, time.max, tzinfo=UTC)
        result = await self.db.execute(
            select(Dose.scheduled_at, Pet.id, Pet.name)
            .join(Medication, Dose.medication_id == Medication.id)
            .join(Pet, Medication.pet_id == Pet.id)
            .where(
                and_(
                    Pet.owner_id == owner_id,
                    Dose.scheduled_at >= start_dt,
                    Dose.scheduled_at <= end_dt,
                )
            )
        )
        return [(scheduled_at, pet_id, pet_name) for scheduled_at, pet_id, pet_name in result.all()]
