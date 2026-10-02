from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.vet_appointment import VetAppointment
from app.repositories.clinic_repo import ClinicRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.vet_appointment_repo import VetAppointmentRepository
from app.schemas.vet_appointment import VetAppointmentCreate, VetAppointmentUpdate


class VetAppointmentService:
    def __init__(self, db: AsyncSession):
        self.repo = VetAppointmentRepository(db)
        self.pet_repo = PetRepository(db)
        self.clinic_repo = ClinicRepository(db)

    async def _validate_pet(self, pet_id: int, owner_id: int) -> None:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

    async def _validate_clinic(self, clinic_id: int, owner_id: int) -> None:
        clinic = await self.clinic_repo.get_by_id(clinic_id)
        if not clinic or clinic.is_deleted or clinic.owner_id != owner_id:
            raise NotFoundError("Clinic not found")

    async def get_appointments(self, owner_id: int, pet_id: int | None = None) -> list[VetAppointment]:
        if pet_id is not None:
            await self._validate_pet(pet_id, owner_id)
        return await self.repo.get_all_by_owner(owner_id, pet_id)

    async def get_appointment(self, appointment_id: int, owner_id: int) -> VetAppointment:
        appointment = await self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")
        await self._validate_pet(appointment.pet_id, owner_id)
        return appointment

    async def create_appointment(self, owner_id: int, data: VetAppointmentCreate) -> VetAppointment:
        await self._validate_pet(data.pet_id, owner_id)
        await self._validate_clinic(data.clinic_id, owner_id)
        return await self.repo.create(data)

    async def update_appointment(
        self, appointment_id: int, owner_id: int, data: VetAppointmentUpdate
    ) -> VetAppointment:
        appointment = await self.get_appointment(appointment_id, owner_id)
        if data.clinic_id is not None:
            await self._validate_clinic(data.clinic_id, owner_id)

        new_appointment_at = data.appointment_at or self._as_utc(appointment.appointment_at)
        new_reminder_at = data.reminder_at or self._as_utc(appointment.reminder_at)
        if new_reminder_at > new_appointment_at:
            raise BadRequestError("reminder_at must not be after appointment_at")

        return await self.repo.update(appointment, data)

    async def delete_appointment(self, appointment_id: int, owner_id: int) -> None:
        appointment = await self.get_appointment(appointment_id, owner_id)
        await self.repo.delete(appointment)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """SQLite (used in tests) drops tzinfo on round-trip even for tz-aware
        columns; everything we store here is UTC, so a naive value just needs it
        reattached."""
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
