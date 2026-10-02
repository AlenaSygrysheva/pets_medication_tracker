from datetime import datetime

from pydantic import BaseModel, ValidationInfo, field_validator

from app.schemas.clinic import ClinicResponse


class VetAppointmentBase(BaseModel):
    clinic_id: int
    doctor_name: str | None = None
    appointment_at: datetime
    reminder_at: datetime
    comments: str | None = None

    @field_validator("reminder_at")
    @classmethod
    def reminder_not_after_appointment(cls, v: datetime, info: ValidationInfo) -> datetime:
        appointment_at = info.data.get("appointment_at")
        if appointment_at is not None and v > appointment_at:
            raise ValueError("reminder_at must not be after appointment_at")
        return v


class VetAppointmentCreate(VetAppointmentBase):
    pet_id: int


class VetAppointmentUpdate(BaseModel):
    clinic_id: int | None = None
    doctor_name: str | None = None
    appointment_at: datetime | None = None
    reminder_at: datetime | None = None
    comments: str | None = None


class VetAppointmentResponse(BaseModel):
    id: int
    pet_id: int
    doctor_name: str | None
    appointment_at: datetime
    reminder_at: datetime
    comments: str | None
    clinic: ClinicResponse

    model_config = {"from_attributes": True}
