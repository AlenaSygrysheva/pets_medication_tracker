from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.calendar import CalendarDayResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/pet/{pet_id}/{day}", response_model=CalendarDayResponse)
async def get_calendar_day(
    pet_id: int,
    day: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarDayResponse:
    return await CalendarService(db).get_day(pet_id, current_user.id, day)
