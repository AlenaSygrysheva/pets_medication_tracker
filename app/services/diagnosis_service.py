from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.diagnosis import Diagnosis
from app.repositories.diagnosis_repo import DiagnosisRepository
from app.repositories.pet_repo import PetRepository
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisUpdate


class DiagnosisService:
    def __init__(self, db: AsyncSession):
        self.repo = DiagnosisRepository(db)
        self.pet_repo = PetRepository(db)

    async def _validate_pet(self, pet_id: int, owner_id: int) -> None:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

    async def get_diagnoses(self, owner_id: int, pet_id: int | None = None) -> list[Diagnosis]:
        if pet_id is not None:
            await self._validate_pet(pet_id, owner_id)
        return await self.repo.get_all_by_owner(owner_id, pet_id)

    async def get_diagnosis(self, diagnosis_id: int, owner_id: int) -> Diagnosis:
        diagnosis = await self.repo.get_by_id(diagnosis_id)
        if not diagnosis:
            raise NotFoundError("Diagnosis not found")
        await self._validate_pet(diagnosis.pet_id, owner_id)
        return diagnosis

    async def create_diagnosis(self, owner_id: int, data: DiagnosisCreate) -> Diagnosis:
        await self._validate_pet(data.pet_id, owner_id)
        return await self.repo.create(data)

    async def update_diagnosis(
        self, diagnosis_id: int, owner_id: int, data: DiagnosisUpdate
    ) -> Diagnosis:
        diagnosis = await self.get_diagnosis(diagnosis_id, owner_id)

        new_confirmed = data.confirmed_by_vet if data.confirmed_by_vet is not None else diagnosis.confirmed_by_vet
        new_doctor_name = data.doctor_name if data.doctor_name is not None else diagnosis.doctor_name
        if new_confirmed and not new_doctor_name:
            raise BadRequestError("doctor_name is required when confirmed_by_vet is true")

        return await self.repo.update(diagnosis, data)

    async def delete_diagnosis(self, diagnosis_id: int, owner_id: int) -> None:
        diagnosis = await self.get_diagnosis(diagnosis_id, owner_id)
        await self.repo.delete(diagnosis)
