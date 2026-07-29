from datetime import datetime

from pydantic import BaseModel, field_validator


class BugReportCreate(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message must not be empty")
        return v


class BugReportUpdate(BaseModel):
    is_resolved: bool


class BugReportUser(BaseModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}


class BugReportResponse(BaseModel):
    id: int
    user: BugReportUser
    message: str
    is_resolved: bool
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}
