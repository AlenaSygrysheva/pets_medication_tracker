from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.medication import Medication
from app.models.user import User
from app.schemas.medication import (
    MedicationCreate,
    MedicationResponse,
    MedicationStatsResponse,
    MedicationUpdate,
)
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("/pet/{pet_id}", response_model=list[MedicationResponse])
async def list_medications(
    pet_id: int,
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Medication]:
    return await MedicationService(db).get_medications(pet_id, current_user.id, active_only)


@router.get("/pet/{pet_id}/stats", response_model=list[MedicationStatsResponse])
async def list_ended_medication_stats(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationStatsResponse]:
    """Сводка по завершённым курсам (отменённым или закончившимся по дате)."""
    return await MedicationService(db).get_ended_medications_stats(pet_id, current_user.id)


@router.post("", response_model=MedicationResponse, status_code=201)
async def create_medication(
    data: MedicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medication:
    return await MedicationService(db).create_medication(current_user.id, data)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medication:
    return await MedicationService(db).get_medication(medication_id, current_user.id)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    data: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medication:
    return await MedicationService(db).update_medication(medication_id, current_user.id, data)


@router.post("/{medication_id}/cancel", response_model=MedicationResponse)
async def cancel_medication(
    medication_id: int,
    as_of_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medication:
    """Отменить курс лечения на дату as_of_date (по умолчанию — сегодня):
    дозы после этой даты стираются, дозы до неё и в этот день помечаются cancelled."""
    return await MedicationService(db).cancel_medication(medication_id, current_user.id, as_of_date)


@router.delete("/{medication_id}", status_code=204)
async def delete_medication(
    medication_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await MedicationService(db).delete_medication(medication_id, current_user.id)
