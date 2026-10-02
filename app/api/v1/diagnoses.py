from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.diagnosis import Diagnosis
from app.models.user import User
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisResponse, DiagnosisUpdate
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


@router.get("", response_model=list[DiagnosisResponse])
async def list_diagnoses(
    pet_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Diagnosis]:
    return await DiagnosisService(db).get_diagnoses(current_user.id, pet_id)


@router.post("", response_model=DiagnosisResponse, status_code=201)
async def create_diagnosis(
    data: DiagnosisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Diagnosis:
    return await DiagnosisService(db).create_diagnosis(current_user.id, data)


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
async def get_diagnosis(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Diagnosis:
    return await DiagnosisService(db).get_diagnosis(diagnosis_id, current_user.id)


@router.patch("/{diagnosis_id}", response_model=DiagnosisResponse)
async def update_diagnosis(
    diagnosis_id: int,
    data: DiagnosisUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Diagnosis:
    return await DiagnosisService(db).update_diagnosis(diagnosis_id, current_user.id, data)


@router.delete("/{diagnosis_id}", status_code=204)
async def delete_diagnosis(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await DiagnosisService(db).delete_diagnosis(diagnosis_id, current_user.id)
