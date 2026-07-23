from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.drug import Drug
from app.models.user import User
from app.schemas.drug import DrugCreate, DrugResponse, DrugUpdate
from app.services.drug_service import DrugService

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("", response_model=list[DrugResponse])
async def list_drugs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Drug]:
    return await DrugService(db).get_drugs(current_user.id)


@router.post("", response_model=DrugResponse, status_code=201)
async def create_drug(
    data: DrugCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Drug:
    return await DrugService(db).create_drug(current_user.id, data)


@router.get("/{drug_id}", response_model=DrugResponse)
async def get_drug(
    drug_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Drug:
    return await DrugService(db).get_drug(drug_id, current_user.id)


@router.patch("/{drug_id}", response_model=DrugResponse)
async def update_drug(
    drug_id: int,
    data: DrugUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Drug:
    return await DrugService(db).update_drug(drug_id, current_user.id, data)


@router.delete("/{drug_id}", status_code=204)
async def delete_drug(
    drug_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await DrugService(db).delete_drug(drug_id, current_user.id)
