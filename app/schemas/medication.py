from datetime import date

from pydantic import BaseModel, ValidationInfo, field_validator


class MedicationBase(BaseModel):
    name: str
    dosage: str
    frequency_per_day: int = 1
    start_date: date
    end_date: date | None = None
    instructions: str | None = None

    @field_validator("frequency_per_day")
    @classmethod
    def frequency_valid(cls, v: int) -> int:
        if v < 1 or v > 24:
            raise ValueError("Frequency must be between 1 and 24 times per day")
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date | None, info: ValidationInfo) -> date | None:
        if v and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class MedicationCreate(MedicationBase):
    pet_id: int


class MedicationUpdate(BaseModel):
    name: str | None = None
    dosage: str | None = None
    frequency_per_day: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    instructions: str | None = None
    is_active: bool | None = None


class MedicationResponse(MedicationBase):
    id: int
    pet_id: int
    is_active: bool

    model_config = {"from_attributes": True}
