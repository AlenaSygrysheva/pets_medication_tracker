from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.calendar import DoseActionRequest, DoseResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/doses", tags=["doses"])


@router.patch("/{dose_id}", response_model=DoseResponse)
async def update_dose(
    dose_id: int,
    data: DoseActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DoseResponse:
    return await CalendarService(db).record_dose(dose_id, current_user.id, data)
