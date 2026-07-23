from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.drug import Drug
from app.repositories.drug_repo import DrugRepository
from app.schemas.drug import DrugCreate, DrugUpdate


class DrugService:
    def __init__(self, db: AsyncSession):
        self.repo = DrugRepository(db)

    async def get_drugs(self, owner_id: int) -> list[Drug]:
        return await self.repo.get_all_by_owner(owner_id)

    async def get_drug(self, drug_id: int, owner_id: int) -> Drug:
        drug = await self.repo.get_by_id(drug_id)
        if not drug or drug.is_deleted:
            raise NotFoundError("Drug not found")
        if drug.owner_id != owner_id:
            raise ForbiddenError("Access denied")
        return drug

    async def create_drug(self, owner_id: int, data: DrugCreate) -> Drug:
        existing = await self.repo.get_by_name_and_strength(owner_id, data.name, data.strength)
        if existing:
            raise ConflictError(f"Препарат «{data.name} {data.strength}» уже есть в каталоге")
        return await self.repo.create(owner_id, data)

    async def update_drug(self, drug_id: int, owner_id: int, data: DrugUpdate) -> Drug:
        drug = await self.get_drug(drug_id, owner_id)

        new_name = data.name if data.name is not None else drug.name
        new_strength = data.strength if data.strength is not None else drug.strength
        if (new_name, new_strength) != (drug.name, drug.strength):
            existing = await self.repo.get_by_name_and_strength(owner_id, new_name, new_strength)
            if existing and existing.id != drug.id:
                raise ConflictError(f"Препарат «{new_name} {new_strength}» уже есть в каталоге")

        return await self.repo.update(drug, data)

    async def delete_drug(self, drug_id: int, owner_id: int) -> None:
        drug = await self.get_drug(drug_id, owner_id)
        if await self.repo.has_active_courses(drug_id):
            raise ConflictError(
                "Нельзя удалить препарат: он используется в активном курсе лечения. "
                "Дождитесь завершения курса лечения или отмените этот курс."
            )
        await self.repo.soft_delete(drug)
