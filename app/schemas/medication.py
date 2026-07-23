from datetime import date, time

from pydantic import BaseModel, ValidationInfo, field_validator

from app.schemas.drug import DrugResponse


def _parse_reminder_times(v: list[str]) -> list[str]:
    if not v:
        raise ValueError("reminder_times cannot be empty")
    parsed = []
    for t in v:
        try:
            parsed.append(time.fromisoformat(t))
        except ValueError as e:
            raise ValueError(f"Invalid time format '{t}', expected HH:MM") from e
    return [t.strftime("%H:%M") for t in sorted(parsed)]


class MedicationBase(BaseModel):
    drug_id: int
    dosage: str
    frequency_per_day: int = 1
    reminder_times: list[str] | None = None
    start_date: date
    end_date: date | None = None
    instructions: str | None = None

    @field_validator("frequency_per_day")
    @classmethod
    def frequency_valid(cls, v: int) -> int:
        if v < 1 or v > 24:
            raise ValueError("Frequency must be between 1 and 24 times per day")
        return v

    @field_validator("reminder_times")
    @classmethod
    def reminder_times_valid(cls, v: list[str] | None, info: ValidationInfo) -> list[str] | None:
        if v is None:
            return v
        parsed = _parse_reminder_times(v)
        freq = info.data.get("frequency_per_day")
        if freq is not None and len(parsed) != freq:
            raise ValueError("Number of reminder_times must match frequency_per_day")
        return parsed

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date | None, info: ValidationInfo) -> date | None:
        if v and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class MedicationCreate(MedicationBase):
    pet_id: int


class MedicationUpdate(BaseModel):
    drug_id: int | None = None
    dosage: str | None = None
    frequency_per_day: int | None = None
    reminder_times: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    instructions: str | None = None
    is_active: bool | None = None

    @field_validator("reminder_times")
    @classmethod
    def reminder_times_valid(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return _parse_reminder_times(v)


class MedicationResponse(MedicationBase):
    id: int
    pet_id: int
    is_active: bool
    drug: DrugResponse

    model_config = {"from_attributes": True}


class MedicationStatsResponse(BaseModel):
    medication_id: int
    medication_name: str
    pet_id: int
    start_date: date
    end_date: date | None
    ended_reason: str
    taken: int
    skipped: int
    missed: int
    cancelled: int
    total: int
