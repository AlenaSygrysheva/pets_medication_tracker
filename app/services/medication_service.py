import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.repositories.dose_repo import DoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.pet_repo import PetRepository
from app.schemas.medication import MedicationCreate, MedicationStatsResponse, MedicationUpdate

logger = logging.getLogger(__name__)


class MedicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MedicationRepository(db)
        self.pet_repo = PetRepository(db)
        self.dose_repo = DoseRepository(db)

    async def get_medications(self, pet_id: int, owner_id: int, active_only: bool = False) -> list[Medication]:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")
        return await self.repo.get_all_by_pet(pet_id, active_only)

    async def get_medication(self, medication_id: int, owner_id: int) -> Medication:
        med = await self.repo.get_by_id(medication_id)
        if not med:
            raise NotFoundError("Medication not found")
        pet = await self.pet_repo.get_by_id(med.pet_id)
        if not pet or pet.owner_id != owner_id:
            raise ForbiddenError("Access denied")
        return med

    async def create_medication(self, owner_id: int, data: MedicationCreate) -> Medication:
        pet = await self.pet_repo.get_by_id(data.pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

        if data.reminder_times is None:
            data = data.model_copy(update={"reminder_times": self._default_times(data.frequency_per_day)})

        medication = await self.repo.create(data)
        async with self.db.begin_nested():
            await self._generate_doses(medication)
        logger.info("Generated doses for medication id=%d pet_id=%d", medication.id, medication.pet_id)
        await cache_delete_pattern(f"calendar:{medication.pet_id}:*")
        return medication

    async def cancel_medication(
        self, medication_id: int, owner_id: int, as_of: date | None = None
    ) -> Medication:
        med = await self.get_medication(medication_id, owner_id)
        as_of = as_of or date.today()
        erased = await self.dose_repo.delete_pending_after(med.id, as_of)
        cancelled = await self.dose_repo.cancel_pending_up_to(med.id, as_of)
        med.is_active = False
        await self.db.flush()
        logger.info(
            "Cancelled medication id=%d as_of=%s: %d future doses erased, %d doses marked cancelled",
            med.id, as_of, erased, cancelled,
        )
        await cache_delete_pattern(f"calendar:{med.pet_id}:*")
        return med

    async def update_medication(self, medication_id: int, owner_id: int, data: MedicationUpdate) -> Medication:
        med = await self.get_medication(medication_id, owner_id)

        new_frequency = data.frequency_per_day if data.frequency_per_day is not None else med.frequency_per_day
        new_times = data.reminder_times if data.reminder_times is not None else med.reminder_times
        if len(new_times) != new_frequency:
            raise BadRequestError("Number of reminder_times must match frequency_per_day")

        regen = (
            (data.start_date is not None and data.start_date != med.start_date)
            or (data.frequency_per_day is not None and data.frequency_per_day != med.frequency_per_day)
            or (data.reminder_times is not None and data.reminder_times != med.reminder_times)
        )
        updated = await self.repo.update(med, data)
        if regen:
            await self.dose_repo.delete_pending_for_medication(updated.id)
            async with self.db.begin_nested():
                await self._generate_doses(updated)
        await cache_delete_pattern(f"calendar:{updated.pet_id}:*")
        return updated

    async def delete_medication(self, medication_id: int, owner_id: int) -> None:
        """Soft-delete: hides the medication from the medications tab while keeping
        already-recorded doses (taken/skipped/missed) visible in the calendar."""
        med = await self.get_medication(medication_id, owner_id)
        await self.dose_repo.delete_pending_for_medication(med.id)
        await self.repo.soft_delete(med)
        await cache_delete_pattern(f"calendar:{med.pet_id}:*")

    async def get_medication_stats(self, medication_id: int, owner_id: int) -> MedicationStatsResponse:
        med = await self.get_medication(medication_id, owner_id)
        return await self._build_stats(med)

    async def get_ended_medications_stats(
        self, pet_id: int, owner_id: int
    ) -> list[MedicationStatsResponse]:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")
        ended = await self.repo.get_ended_by_pet(pet_id, date.today())
        return [await self._build_stats(med) for med in ended]

    async def _build_stats(self, med: Medication) -> MedicationStatsResponse:
        counts = await self.dose_repo.get_status_counts(med.id)
        cancelled_early = not med.is_active
        return MedicationStatsResponse(
            medication_id=med.id,
            medication_name=med.name,
            pet_id=med.pet_id,
            start_date=med.start_date,
            end_date=med.end_date,
            ended_reason="cancelled" if cancelled_early else "completed",
            taken=counts.get(DoseStatus.TAKEN.value, 0),
            skipped=counts.get(DoseStatus.SKIPPED.value, 0),
            missed=counts.get(DoseStatus.MISSED.value, 0),
            cancelled=counts.get(DoseStatus.CANCELLED.value, 0),
            total=sum(counts.values()),
        )

    @staticmethod
    def _default_times(frequency_per_day: int) -> list[str]:
        interval_hours = 24 // frequency_per_day
        return [f"{min(8 + i * interval_hours, 23):02d}:00" for i in range(frequency_per_day)]

    async def _generate_doses(self, medication: Medication) -> None:
        end = medication.end_date or (medication.start_date + timedelta(days=30))
        doses: list[Dose] = []

        times = [datetime.strptime(t, "%H:%M").time() for t in medication.reminder_times]
        current_date = medication.start_date

        while current_date <= end:
            for t in times:
                scheduled = datetime.combine(current_date, t, tzinfo=UTC)
                doses.append(
                    Dose(
                        medication_id=medication.id,
                        scheduled_at=scheduled,
                        status=DoseStatus.PENDING,
                    )
                )
            current_date += timedelta(days=1)

        await self.dose_repo.create_bulk(doses)
