from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pet import Pet
from app.models.vet_appointment import VetAppointment
from app.schemas.vet_appointment import VetAppointmentCreate, VetAppointmentUpdate


class VetAppointmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _with_clinic():
        return select(VetAppointment).options(selectinload(VetAppointment.clinic))

    async def get_by_id(self, appointment_id: int) -> VetAppointment | None:
        result = await self.db.execute(
            self._with_clinic().where(VetAppointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int, pet_id: int | None = None) -> list[VetAppointment]:
        q = self._with_clinic().join(Pet, VetAppointment.pet_id == Pet.id).where(Pet.owner_id == owner_id)
        if pet_id is not None:
            q = q.where(VetAppointment.pet_id == pet_id)
        result = await self.db.execute(q.order_by(VetAppointment.appointment_at))
        return list(result.scalars().all())

    async def get_appointment_dates_by_owner(
        self, owner_id: int, start: date, end: date
    ) -> set[date]:
        start_dt = datetime.combine(start, time.min, tzinfo=UTC)
        end_dt = datetime.combine(end, time.max, tzinfo=UTC)
        result = await self.db.execute(
            select(VetAppointment.appointment_at)
            .join(Pet, VetAppointment.pet_id == Pet.id)
            .where(
                Pet.owner_id == owner_id,
                VetAppointment.appointment_at >= start_dt,
                VetAppointment.appointment_at <= end_dt,
            )
        )
        return {scheduled.date() for (scheduled,) in result.all()}

    async def create(self, data: VetAppointmentCreate) -> VetAppointment:
        appointment = VetAppointment(**data.model_dump())
        self.db.add(appointment)
        await self.db.flush()
        result = await self.db.execute(
            self._with_clinic().where(VetAppointment.id == appointment.id)
        )
        return result.scalar_one()

    async def update(self, appointment: VetAppointment, data: VetAppointmentUpdate) -> VetAppointment:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(appointment, field, value)
        await self.db.flush()
        result = await self.db.execute(
            self._with_clinic().where(VetAppointment.id == appointment.id)
        )
        return result.scalar_one()

    async def delete(self, appointment: VetAppointment) -> None:
        await self.db.delete(appointment)
        await self.db.flush()
