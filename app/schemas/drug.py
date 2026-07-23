from pydantic import BaseModel


class DrugBase(BaseModel):
    name: str
    purpose: str
    strength: str


class DrugCreate(DrugBase):
    pass


class DrugUpdate(BaseModel):
    name: str | None = None
    purpose: str | None = None
    strength: str | None = None


class DrugResponse(DrugBase):
    id: int

    model_config = {"from_attributes": True}
