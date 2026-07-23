from datetime import date, datetime

from pydantic import BaseModel

from app.models.dose import DoseStatus


class DoseSlot(BaseModel):
    dose_id: int | None = None
    medication_id: int
    medication_name: str
    dosage: str
    scheduled_at: datetime
    status: DoseStatus
    notes: str | None = None

    model_config = {"from_attributes": True}


class CalendarDayResponse(BaseModel):
    date: date
    pet_id: int
    pet_name: str
    doses: list[DoseSlot]
    total: int
    taken: int
    pending: int
    missed: int


class DoseActionRequest(BaseModel):
    status: DoseStatus
    notes: str | None = None
    taken_at: datetime | None = None


class DoseResponse(BaseModel):
    id: int
    medication_id: int
    scheduled_at: datetime
    taken_at: datetime | None
    status: DoseStatus
    notes: str | None

    model_config = {"from_attributes": True}


class CalendarMonthPetEntry(BaseModel):
    pet_id: int
    pet_name: str
    initial: str


class CalendarMonthDay(BaseModel):
    date: date
    pets: list[CalendarMonthPetEntry]


class CalendarMonthResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarMonthDay]
