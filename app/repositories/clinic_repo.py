from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.vet_appointment import VetAppointment
from app.schemas.clinic import ClinicCreate, ClinicUpdate


class ClinicRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, clinic_id: int) -> Clinic | None:
        result = await self.db.execute(select(Clinic).where(Clinic.id == clinic_id))
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int, include_deleted: bool = False) -> list[Clinic]:
        q = select(Clinic).where(Clinic.owner_id == owner_id)
        if not include_deleted:
            q = q.where(Clinic.is_deleted.is_(False))
        result = await self.db.execute(q.order_by(Clinic.name))
        return list(result.scalars().all())

    async def get_by_name(self, owner_id: int, name: str) -> Clinic | None:
        result = await self.db.execute(
            select(Clinic).where(
                and_(
                    Clinic.owner_id == owner_id,
                    Clinic.name == name,
                    Clinic.is_deleted.is_(False),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, owner_id: int, data: ClinicCreate) -> Clinic:
        clinic = Clinic(owner_id=owner_id, **data.model_dump())
        self.db.add(clinic)
        await self.db.flush()
        await self.db.refresh(clinic)
        return clinic

    async def update(self, clinic: Clinic, data: ClinicUpdate) -> Clinic:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(clinic, field, value)
        await self.db.flush()
        await self.db.refresh(clinic)
        return clinic

    async def soft_delete(self, clinic: Clinic) -> None:
        clinic.is_deleted = True
        await self.db.flush()

    async def has_upcoming_appointments(self, clinic_id: int) -> bool:
        result = await self.db.execute(
            select(VetAppointment.id)
            .where(
                VetAppointment.clinic_id == clinic_id,
                VetAppointment.appointment_at >= datetime.now(UTC),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
