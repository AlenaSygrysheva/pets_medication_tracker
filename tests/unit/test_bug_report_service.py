"""Unit tests for BugReportService — repository is mocked."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import NotFoundError
from app.models.bug_report import BugReport
from app.schemas.bug_report import BugReportCreate
from app.services.bug_report_service import BugReportService


def _make_report(
    report_id: int = 1,
    user_id: int = 1,
    message: str = "Что-то сломалось",
    is_resolved: bool = False,
) -> BugReport:
    report = MagicMock(spec=BugReport)
    report.id = report_id
    report.user_id = user_id
    report.message = message
    report.is_resolved = is_resolved
    return report


class TestBugReportServiceCreate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = BugReportService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_create_report_calls_repo_with_user_and_message(self) -> None:
        self.service.repo.create = AsyncMock(return_value=_make_report(user_id=7))
        data = BugReportCreate(message="Кнопка не работает")

        result = await self.service.create_report(user_id=7, data=data)

        self.service.repo.create.assert_awaited_once_with(7, "Кнопка не работает")
        self.assertEqual(result.user_id, 7)


class TestBugReportServiceList(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = BugReportService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_list_reports_passes_filter_through(self) -> None:
        self.service.repo.get_all = AsyncMock(return_value=[_make_report()])
        result = await self.service.list_reports(is_resolved=False)
        self.service.repo.get_all.assert_awaited_once_with(False)
        self.assertEqual(len(result), 1)

    async def test_list_reports_no_filter(self) -> None:
        self.service.repo.get_all = AsyncMock(return_value=[])
        result = await self.service.list_reports()
        self.service.repo.get_all.assert_awaited_once_with(None)
        self.assertEqual(result, [])


class TestBugReportServiceSetResolved(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = BugReportService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_set_resolved_updates_existing_report(self) -> None:
        report = _make_report(report_id=3)
        resolved = _make_report(report_id=3, is_resolved=True)
        self.service.repo.get_by_id = AsyncMock(return_value=report)
        self.service.repo.set_resolved = AsyncMock(return_value=resolved)

        result = await self.service.set_resolved(3, True)

        self.service.repo.set_resolved.assert_awaited_once_with(report, True)
        self.assertTrue(result.is_resolved)

    async def test_set_resolved_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.set_resolved(999, True)


if __name__ == "__main__":
    unittest.main()
