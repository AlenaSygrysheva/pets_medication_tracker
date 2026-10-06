import re

from pydantic import BaseModel, field_validator

_PHONE_PATTERN = re.compile(r"^\d{7,15}$")


def _validate_phone_digits(v: str) -> str:
    if not _PHONE_PATTERN.fullmatch(v):
        raise ValueError("phone must contain only digits (7-15 digits, no spaces or symbols)")
    return v


def _required_text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    return v


def _optional_text(v: str | None) -> str | None:
    """Blank means "no value": "" / "   " are stored as NULL."""
    if v is None:
        return None
    return v.strip() or None


class ClinicBase(BaseModel):
    name: str
    address: str
    phone: str
    website: str | None = None

    @field_validator("name", "address")
    @classmethod
    def not_blank(cls, v: str) -> str:
        return _required_text(v)

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        return _validate_phone_digits(v)

    @field_validator("website")
    @classmethod
    def blank_website_is_none(cls, v: str | None) -> str | None:
        return _optional_text(v)


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    """Partial update: only the fields the client actually sent are applied
    (the repo dumps with exclude_unset). Sending `website: null` or "" clears it;
    the required fields can be changed but not cleared."""

    name: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None

    # Validators run only for keys present in the request, so a None here is an
    # explicit `null` from the client, not an omitted field.
    @field_validator("name", "address")
    @classmethod
    def not_blank(cls, v: str | None) -> str:
        if v is None:
            raise ValueError("required field, cannot be cleared")
        return _required_text(v)

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str | None) -> str:
        if v is None:
            raise ValueError("required field, cannot be cleared")
        return _validate_phone_digits(v)

    @field_validator("website")
    @classmethod
    def blank_website_is_none(cls, v: str | None) -> str | None:
        return _optional_text(v)


class ClinicResponse(BaseModel):
    # Not derived from ClinicBase on purpose: the strict phone check is for input only.
    # Re-running it on output turns any legacy row (saved before the check existed) into a 500.
    id: int
    name: str
    address: str
    phone: str
    website: str | None = None

    model_config = {"from_attributes": True}
