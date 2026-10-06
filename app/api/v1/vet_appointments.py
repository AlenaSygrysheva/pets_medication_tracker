from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.completed_vet_visit import CompletedVetVisit
from app.models.user import User
from app.models.vet_appointment import VetAppointment
from app.schemas.vet_appointment import (
    CompletedVetVisitResponse,
    VetAppointmentCreate,
    VetAppointmentResponse,
    VetAppointmentUpdate,
)
from app.services.vet_appointment_service import VetAppointmentService

router = APIRouter(prefix="/vet-appointments", tags=["vet-appointments"])


@router.get("", response_model=list[VetAppointmentResponse])
async def list_vet_appointments(
    pet_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VetAppointment]:
    return await VetAppointmentService(db).get_appointments(current_user.id, pet_id)


@router.post("", response_model=VetAppointmentResponse, status_code=201)
async def create_vet_appointment(
    data: VetAppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VetAppointment:
    return await VetAppointmentService(db).create_appointment(current_user.id, data)


# Declared before "/{appointment_id}" so "completed" isn't parsed as an id.
@router.get("/completed", response_model=list[CompletedVetVisitResponse])
async def list_completed_vet_visits(
    pet_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CompletedVetVisit]:
    return await VetAppointmentService(db).get_completed_visits(current_user.id, pet_id)


@router.post("/{appointment_id}/complete", response_model=CompletedVetVisitResponse)
async def complete_vet_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompletedVetVisit:
    return await VetAppointmentService(db).complete_appointment(appointment_id, current_user.id)


@router.get("/{appointment_id}", response_model=VetAppointmentResponse)
async def get_vet_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VetAppointment:
    return await VetAppointmentService(db).get_appointment(appointment_id, current_user.id)


@router.patch("/{appointment_id}", response_model=VetAppointmentResponse)
async def update_vet_appointment(
    appointment_id: int,
    data: VetAppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VetAppointment:
    return await VetAppointmentService(db).update_appointment(appointment_id, current_user.id, data)


@router.delete("/{appointment_id}", status_code=204)
async def delete_vet_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await VetAppointmentService(db).delete_appointment(appointment_id, current_user.id)
