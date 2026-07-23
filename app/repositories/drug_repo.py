from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dose import Dose, DoseStatus
from app.models.drug import Drug
from app.models.medication import Medication
from app.schemas.drug import DrugCreate, DrugUpdate


class DrugRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, drug_id: int) -> Drug | None:
        result = await self.db.execute(select(Drug).where(Drug.id == drug_id))
        return result.scalar_one_or_none()

    async def get_all_by_owner(self, owner_id: int, include_deleted: bool = False) -> list[Drug]:
        q = select(Drug).where(Drug.owner_id == owner_id)
        if not include_deleted:
            q = q.where(Drug.is_deleted.is_(False))
        result = await self.db.execute(q.order_by(Drug.name))
        return list(result.scalars().all())

    async def get_by_name_and_strength(self, owner_id: int, name: str, strength: str) -> Drug | None:
        result = await self.db.execute(
            select(Drug).where(
                and_(
                    Drug.owner_id == owner_id,
                    Drug.name == name,
                    Drug.strength == strength,
                    Drug.is_deleted.is_(False),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, owner_id: int, data: DrugCreate) -> Drug:
        drug = Drug(owner_id=owner_id, **data.model_dump())
        self.db.add(drug)
        await self.db.flush()
        await self.db.refresh(drug)
        return drug

    async def update(self, drug: Drug, data: DrugUpdate) -> Drug:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(drug, field, value)
        await self.db.flush()
        await self.db.refresh(drug)
        return drug

    async def soft_delete(self, drug: Drug) -> None:
        drug.is_deleted = True
        await self.db.flush()

    async def has_active_courses(self, drug_id: int) -> bool:
        """True if some course using this drug is still ongoing — active and with
        pending doses left. A cancelled or fully-resolved course doesn't block deletion."""
        has_pending = (
            select(Dose.id)
            .where(Dose.medication_id == Medication.id, Dose.status == DoseStatus.PENDING)
            .exists()
        )
        result = await self.db.execute(
            select(Medication.id)
            .where(Medication.drug_id == drug_id, Medication.is_active.is_(True), has_pending)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
