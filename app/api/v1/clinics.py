from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.clinic import ClinicCreate, ClinicResponse, ClinicUpdate
from app.services.clinic_service import ClinicService

router = APIRouter(prefix="/clinics", tags=["clinics"])


@router.get("", response_model=list[ClinicResponse])
async def list_clinics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Clinic]:
    return await ClinicService(db).get_clinics(current_user.id)


@router.post("", response_model=ClinicResponse, status_code=201)
async def create_clinic(
    data: ClinicCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    return await ClinicService(db).create_clinic(current_user.id, data)


@router.get("/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(
    clinic_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    return await ClinicService(db).get_clinic(clinic_id, current_user.id)


@router.patch("/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    clinic_id: int,
    data: ClinicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Clinic:
    return await ClinicService(db).update_clinic(clinic_id, current_user.id, data)


@router.delete("/{clinic_id}", status_code=204)
async def delete_clinic(
    clinic_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ClinicService(db).delete_clinic(clinic_id, current_user.id)
