import logging
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.repositories.dose_repo import DoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.pet_repo import PetRepository
from app.schemas.medication import MedicationCreate, MedicationUpdate

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

        medication = await self.repo.create(data)
        async with self.db.begin_nested():
            await self._generate_doses(medication)
        logger.info("Generated doses for medication id=%d pet_id=%d", medication.id, medication.pet_id)
        await cache_delete_pattern(f"calendar:{medication.pet_id}:*")
        return medication

    async def cancel_medication(self, medication_id: int, owner_id: int) -> Medication:
        med = await self.get_medication(medication_id, owner_id)
        cancelled = await self.dose_repo.cancel_pending_doses(med.id)
        med.is_active = False
        await self.db.flush()
        logger.info("Cancelled medication id=%d, %d pending doses cancelled", med.id, cancelled)
        await cache_delete_pattern(f"calendar:{med.pet_id}:*")
        return med

    async def update_medication(self, medication_id: int, owner_id: int, data: MedicationUpdate) -> Medication:
        med = await self.get_medication(medication_id, owner_id)
        regen = data.start_date is not None and data.start_date != med.start_date
        updated = await self.repo.update(med, data)
        if regen:
            await self.dose_repo.delete_pending_for_medication(updated.id)
            async with self.db.begin_nested():
                await self._generate_doses(updated)
        await cache_delete_pattern(f"calendar:{updated.pet_id}:*")
        return updated

    async def delete_medication(self, medication_id: int, owner_id: int) -> None:
        med = await self.get_medication(medication_id, owner_id)
        await cache_delete_pattern(f"calendar:{med.pet_id}:*")
        await self.repo.delete(med)

    async def _generate_doses(self, medication: Medication) -> None:
        end = medication.end_date or (medication.start_date + timedelta(days=30))
        doses: list[Dose] = []

        interval_hours = 24 // medication.frequency_per_day
        current_date = medication.start_date

        while current_date <= end:
            for i in range(medication.frequency_per_day):
                hour = 8 + i * interval_hours
                scheduled = datetime.combine(current_date, time(hour=min(hour, 23), minute=0), tzinfo=UTC)
                doses.append(
                    Dose(
                        medication_id=medication.id,
                        scheduled_at=scheduled,
                        status=DoseStatus.PENDING,
                    )
                )
            current_date += timedelta(days=1)

        await self.dose_repo.create_bulk(doses)
