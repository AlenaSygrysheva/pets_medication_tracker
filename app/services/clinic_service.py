from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.clinic import Clinic
from app.repositories.clinic_repo import ClinicRepository
from app.schemas.clinic import ClinicCreate, ClinicUpdate


class ClinicService:
    def __init__(self, db: AsyncSession):
        self.repo = ClinicRepository(db)

    async def get_clinics(self, owner_id: int) -> list[Clinic]:
        return await self.repo.get_all_by_owner(owner_id)

    async def get_clinic(self, clinic_id: int, owner_id: int) -> Clinic:
        clinic = await self.repo.get_by_id(clinic_id)
        if not clinic or clinic.is_deleted:
            raise NotFoundError("Clinic not found")
        if clinic.owner_id != owner_id:
            raise ForbiddenError("Access denied")
        return clinic

    async def create_clinic(self, owner_id: int, data: ClinicCreate) -> Clinic:
        existing = await self.repo.get_by_name(owner_id, data.name)
        if existing:
            raise ConflictError(f"Клиника «{data.name}» уже есть в каталоге")
        return await self.repo.create(owner_id, data)

    async def update_clinic(self, clinic_id: int, owner_id: int, data: ClinicUpdate) -> Clinic:
        clinic = await self.get_clinic(clinic_id, owner_id)

        new_name = data.name if data.name is not None else clinic.name
        if new_name != clinic.name:
            existing = await self.repo.get_by_name(owner_id, new_name)
            if existing and existing.id != clinic.id:
                raise ConflictError(f"Клиника «{new_name}» уже есть в каталоге")

        return await self.repo.update(clinic, data)

    async def delete_clinic(self, clinic_id: int, owner_id: int) -> None:
        clinic = await self.get_clinic(clinic_id, owner_id)
        if await self.repo.has_upcoming_appointments(clinic_id):
            raise ConflictError(
                "Нельзя удалить клинику: на неё запланирован приём врача. "
                "Отмените или перенесите приём, затем повторите удаление."
            )
        await self.repo.soft_delete(clinic)
