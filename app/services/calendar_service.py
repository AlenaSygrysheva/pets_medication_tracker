import calendar as calendar_module
from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dose import DoseStatus
from app.repositories.dose_repo import DoseRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.vet_appointment_repo import VetAppointmentRepository
from app.schemas.calendar import (
    CalendarDayResponse,
    CalendarMonthDay,
    CalendarMonthPetEntry,
    CalendarMonthResponse,
    DayStatus,
    DoseActionRequest,
    DoseResponse,
    DoseSlot,
)
from app.services.medication_service import MedicationService

CALENDAR_TTL = 300

_UNRESOLVED_STATUSES = (DoseStatus.MISSED, DoseStatus.SKIPPED)


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.pet_repo = PetRepository(db)
        self.dose_repo = DoseRepository(db)
        self.vet_appointment_repo = VetAppointmentRepository(db)
        self.medication_service = MedicationService(db)

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
                medication_name=f"{d.medication.drug.name} {d.medication.drug.strength}",
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

    async def get_month_summary(self, owner_id: int, year: int, month: int) -> CalendarMonthResponse:
        start = date(year, month, 1)
        end = date(year, month, calendar_module.monthrange(year, month)[1])
        rows = await self.dose_repo.get_month_doses(owner_id, start, end)
        vet_appointment_dates = await self.vet_appointment_repo.get_appointment_dates_by_owner(
            owner_id, start, end
        )

        pets_by_day: dict[date, dict[int, str]] = defaultdict(dict)
        statuses_by_day: dict[date, list[DoseStatus]] = defaultdict(list)
        for scheduled_at, pet_id, pet_name, status in rows:
            day = scheduled_at.date()
            pets_by_day[day][pet_id] = pet_name
            statuses_by_day[day].append(status)

        all_days = set(pets_by_day.keys()) | vet_appointment_dates
        days = [
            CalendarMonthDay(
                date=day,
                pets=[
                    CalendarMonthPetEntry(pet_id=pid, pet_name=name, initial=name[0].upper())
                    for pid, name in sorted(pets_by_day[day].items(), key=lambda entry: entry[1])
                ],
                status=self._day_status(statuses_by_day[day]),
                has_vet_appointment=day in vet_appointment_dates,
            )
            for day in sorted(all_days)
        ]
        return CalendarMonthResponse(year=year, month=month, days=days)

    @staticmethod
    def _day_status(statuses: list[DoseStatus]) -> DayStatus:
        if statuses and all(status == DoseStatus.TAKEN for status in statuses):
            return DayStatus.ALL_TAKEN
        if any(status != DoseStatus.PENDING for status in statuses):
            return DayStatus.PARTIAL
        return DayStatus.NONE

    async def record_dose(self, dose_id: int, owner_id: int, data: DoseActionRequest) -> DoseResponse:
        dose = await self.dose_repo.get_by_id(dose_id)
        if not dose:
            raise NotFoundError("Dose not found")

        pet = await self.pet_repo.get_by_id(dose.medication.pet_id)
        if not pet or pet.owner_id != owner_id:
            raise ForbiddenError("Access denied")

        previous_status = dose.status
        taken_at = data.taken_at or (datetime.now(UTC) if data.status == DoseStatus.TAKEN else None)
        updated = await self.dose_repo.update_status(dose, data.status, taken_at, data.notes)

        if data.status in _UNRESOLVED_STATUSES and previous_status != data.status:
            await self.medication_service.extend_after_unresolved_dose(dose.medication)

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
