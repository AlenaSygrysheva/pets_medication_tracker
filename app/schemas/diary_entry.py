from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.diary_entry import DIARY_TEXT_MAX_LENGTH


def _clean_text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    if len(v) > DIARY_TEXT_MAX_LENGTH:
        raise ValueError(f"must be at most {DIARY_TEXT_MAX_LENGTH} characters")
    return v


class DiaryEntryCreate(BaseModel):
    pet_id: int
    text: str

    @field_validator("text")
    @classmethod
    def text_valid(cls, v: str) -> str:
        return _clean_text(v)


class DiaryEntryUpdate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_valid(cls, v: str) -> str:
        return _clean_text(v)


class DiaryEntryBulkDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class DiaryEntryResponse(BaseModel):
    id: int
    pet_id: int
    text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
