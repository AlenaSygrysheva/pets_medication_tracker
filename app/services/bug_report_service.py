from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.bug_report import BugReport
from app.repositories.bug_report_repo import BugReportRepository
from app.schemas.bug_report import BugReportCreate


class BugReportService:
    def __init__(self, db: AsyncSession):
        self.repo = BugReportRepository(db)

    async def create_report(self, user_id: int, data: BugReportCreate) -> BugReport:
        return await self.repo.create(user_id, data.message)

    async def list_reports(self, is_resolved: bool | None = None) -> list[BugReport]:
        return await self.repo.get_all(is_resolved)

    async def set_resolved(self, bug_report_id: int, is_resolved: bool) -> BugReport:
        bug_report = await self.repo.get_by_id(bug_report_id)
        if not bug_report:
            raise NotFoundError("Bug report not found")
        return await self.repo.set_resolved(bug_report, is_resolved)
