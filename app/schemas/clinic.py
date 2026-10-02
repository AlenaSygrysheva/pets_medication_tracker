import re

from pydantic import BaseModel, field_validator

_PHONE_PATTERN = re.compile(r"^\d{7,15}$")


def _validate_phone_digits(v: str) -> str:
    if not _PHONE_PATTERN.fullmatch(v):
        raise ValueError("phone must contain only digits (7-15 digits, no spaces or symbols)")
    return v


class ClinicBase(BaseModel):
    name: str
    address: str
    phone: str
    website: str | None = None

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        return _validate_phone_digits(v)


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_phone_digits(v)


class ClinicResponse(ClinicBase):
    id: int

    model_config = {"from_attributes": True}
