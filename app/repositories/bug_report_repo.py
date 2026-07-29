from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.models.bug_report import BugReport


class BugReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _with_user() -> Select[tuple[BugReport]]:
        return select(BugReport).options(selectinload(BugReport.user))

    async def get_by_id(self, bug_report_id: int) -> BugReport | None:
        result = await self.db.execute(self._with_user().where(BugReport.id == bug_report_id))
        return result.scalar_one_or_none()

    async def get_all(self, is_resolved: bool | None = None) -> list[BugReport]:
        q = self._with_user().order_by(BugReport.created_at.desc())
        if is_resolved is not None:
            q = q.where(BugReport.is_resolved == is_resolved)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create(self, user_id: int, message: str) -> BugReport:
        bug_report = BugReport(user_id=user_id, message=message)
        self.db.add(bug_report)
        await self.db.flush()
        result = await self.db.execute(self._with_user().where(BugReport.id == bug_report.id))
        return result.scalar_one()

    async def set_resolved(self, bug_report: BugReport, is_resolved: bool) -> BugReport:
        bug_report.is_resolved = is_resolved
        bug_report.resolved_at = datetime.now(UTC) if is_resolved else None
        await self.db.flush()
        result = await self.db.execute(self._with_user().where(BugReport.id == bug_report.id))
        return result.scalar_one()
