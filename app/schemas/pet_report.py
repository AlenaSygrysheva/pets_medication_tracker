from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class PetReportRequest(BaseModel):
    # Treatment period: courses and vet appointments overlapping it go into the card.
    date_from: date
    date_to: date
    diagnosis_ids: list[int] = Field(default_factory=list, max_length=500)
    diary_entry_ids: list[int] = Field(default_factory=list, max_length=500)
    # JS Date.getTimezoneOffset() of the viewer (UTC - local, in minutes). Diary
    # timestamps are real UTC and are shifted by it to match what the app shows.
    tz_offset_minutes: int = Field(default=0, ge=-840, le=840)
    time_format: Literal["24", "12"] = "24"

    @model_validator(mode="after")
    def period_not_reversed(self) -> Self:
        if self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self
