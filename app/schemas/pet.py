from datetime import date

from pydantic import BaseModel, field_validator


class PetBase(BaseModel):
    name: str
    species: str
    breed: str | None = None
    birth_date: date | None = None
    weight_kg: float | None = None
    notes: str | None = None

    @field_validator("weight_kg")
    @classmethod
    def weight_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Weight must be positive")
        return v


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    weight_kg: float | None = None
    notes: str | None = None


class PetResponse(PetBase):
    id: int
    owner_id: int
    avatar_path: str | None = None

    model_config = {"from_attributes": True}
