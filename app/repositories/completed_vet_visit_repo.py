from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.completed_vet_visit import CompletedVetVisit
from app.models.pet import Pet
from app.models.vet_appointment import VetAppointment


class CompletedVetVisitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_owner(
        self, owner_id: int, pet_id: int | None = None
    ) -> list[CompletedVetVisit]:
        q = (
            select(CompletedVetVisit)
            .join(Pet, CompletedVetVisit.pet_id == Pet.id)
            .where(Pet.owner_id == owner_id)
        )
        if pet_id is not None:
            q = q.where(CompletedVetVisit.pet_id == pet_id)
        result = await self.db.execute(q.order_by(CompletedVetVisit.appointment_at.desc()))
        return list(result.scalars().all())

    async def create_from_appointment(self, appointment: VetAppointment) -> CompletedVetVisit:
        """Snapshot the appointment (with its clinic) into the history table.
        Expects `appointment.clinic` to be loaded already."""
        visit = CompletedVetVisit(
            pet_id=appointment.pet_id,
            clinic_name=appointment.clinic.name,
            clinic_address=appointment.clinic.address,
            clinic_phone=appointment.clinic.phone,
            doctor_name=appointment.doctor_name,
            appointment_at=appointment.appointment_at,
            comments=appointment.comments,
        )
        self.db.add(visit)
        await self.db.flush()
        await self.db.refresh(visit)
        return visit
