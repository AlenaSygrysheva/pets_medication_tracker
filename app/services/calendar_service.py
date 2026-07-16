from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dose import DoseStatus
from app.repositories.dose_repo import DoseRepository
from app.repositories.pet_repo import PetRepository
from app.schemas.calendar import CalendarDayResponse, DoseActionRequest, DoseResponse, DoseSlot

CALENDAR_TTL = 300


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.pet_repo = PetRepository(db)
        self.dose_repo = DoseRepository(db)

    async def get_day(self, pet_id: int, owner_id: int, day: date) -> CalendarDayResponse:
        cache_key = f"calendar:{pet_id}:{day.isoformat()}"
        cached = await cache_get(cache_key)
        if cached:
            return CalendarDayResponse(**cached)

        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

        doses = await self.dose_repo.get_doses_for_pet_day(pet_id, day)

        slots = [
            DoseSlot(
                dose_id=d.id,
                medication_id=d.medication_id,
                medication_name=d.medication.name,
                dosage=d.medication.dosage,
                scheduled_at=d.scheduled_at,
                status=d.status,
                notes=d.notes,
            )
            for d in doses
        ]

        response = CalendarDayResponse(
            date=day,
            pet_id=pet_id,
            pet_name=pet.name,
            doses=slots,
            total=len(slots),
            taken=sum(1 for s in slots if s.status == DoseStatus.TAKEN),
            pending=sum(1 for s in slots if s.status == DoseStatus.PENDING),
            missed=sum(1 for s in slots if s.status == DoseStatus.MISSED),
        )

        await cache_set(cache_key, response.model_dump(), CALENDAR_TTL)
        return response

    async def record_dose(self, dose_id: int, owner_id: int, data: DoseActionRequest) -> DoseResponse:
        dose = await self.dose_repo.get_by_id(dose_id)
        if not dose:
            raise NotFoundError("Dose not found")

        pet = await self.pet_repo.get_by_id(dose.medication.pet_id)
        if not pet or pet.owner_id != owner_id:
            raise ForbiddenError("Access denied")

        taken_at = data.taken_at or (datetime.now(UTC) if data.status == DoseStatus.TAKEN else None)
        updated = await self.dose_repo.update_status(dose, data.status, taken_at, data.notes)

        day = dose.scheduled_at.date()
        await cache_delete_pattern(f"calendar:{pet.id}:{day.isoformat()}")

        return DoseResponse(
            id=updated.id,
            medication_id=updated.medication_id,
            scheduled_at=updated.scheduled_at,
            taken_at=updated.taken_at,
            status=updated.status,
            notes=updated.notes,
        )
