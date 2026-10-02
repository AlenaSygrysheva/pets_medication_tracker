from typing import Self

from pydantic import BaseModel, model_validator


class DiagnosisBase(BaseModel):
    name: str
    confirmed_by_vet: bool = False
    doctor_name: str | None = None
    comments: str | None = None

    @model_validator(mode="after")
    def doctor_name_required_if_confirmed(self) -> Self:
        if self.confirmed_by_vet and not self.doctor_name:
            raise ValueError("doctor_name is required when confirmed_by_vet is true")
        return self


class DiagnosisCreate(DiagnosisBase):
    pet_id: int


class DiagnosisUpdate(BaseModel):
    name: str | None = None
    confirmed_by_vet: bool | None = None
    doctor_name: str | None = None
    comments: str | None = None


class DiagnosisResponse(BaseModel):
    id: int
    pet_id: int
    name: str
    confirmed_by_vet: bool
    doctor_name: str | None
    comments: str | None

    model_config = {"from_attributes": True}
