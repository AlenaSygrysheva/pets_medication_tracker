from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.bug_report import BugReport
from app.models.user import User
from app.schemas.bug_report import BugReportCreate, BugReportResponse, BugReportUpdate
from app.services.bug_report_service import BugReportService

router = APIRouter(prefix="/bug-reports", tags=["bug-reports"])


@router.post("", response_model=BugReportResponse, status_code=201)
async def create_bug_report(
    data: BugReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BugReport:
    return await BugReportService(db).create_report(current_user.id, data)


@router.get("", response_model=list[BugReportResponse])
async def list_bug_reports(
    is_resolved: bool | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[BugReport]:
    return await BugReportService(db).list_reports(is_resolved)


@router.patch("/{bug_report_id}", response_model=BugReportResponse)
async def update_bug_report(
    bug_report_id: int,
    data: BugReportUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BugReport:
    return await BugReportService(db).set_resolved(bug_report_id, data.is_resolved)
