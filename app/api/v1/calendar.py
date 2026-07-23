from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.calendar import CalendarDayResponse, CalendarMonthResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/month/{year}/{month}", response_model=CalendarMonthResponse)
async def get_calendar_month(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarMonthResponse:
    """Мини-календарь на месяц: список питомцев (инициалы) по дням, где запланированы приёмы."""
    return await CalendarService(db).get_month_summary(current_user.id, year, month)


@router.get("/pet/{pet_id}/{day}", response_model=CalendarDayResponse)
async def get_calendar_day(
    pet_id: int,
    day: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarDayResponse:
    return await CalendarService(db).get_day(pet_id, current_user.id, day)
