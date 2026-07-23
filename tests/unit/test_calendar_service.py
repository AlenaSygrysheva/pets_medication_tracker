"""Unit tests for CalendarService — DB and Redis are fully mocked."""
import unittest
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.models.pet import Pet
from app.services.calendar_service import CalendarService


def _make_pet(pet_id: int = 1, owner_id: int = 1, name: str = "Барсик") -> Pet:
    p = MagicMock(spec=Pet)
    p.id = pet_id
    p.owner_id = owner_id
    p.name = name
    return p


def _make_dose(
    dose_id: int = 1,
    med_id: int = 1,
    status: DoseStatus = DoseStatus.PENDING,
) -> Dose:
    med = MagicMock(spec=Medication)
    med.name = "TestMed"
    med.dosage = "10mg"
    med.pet_id = 1

    d = MagicMock(spec=Dose)
    d.id = dose_id
    d.medication_id = med_id
    d.medication = med
    d.scheduled_at = datetime(2026, 7, 8, 8, 0, tzinfo=UTC)
    d.status = status
    d.notes = None
    d.taken_at = None
    return d


def _make_service() -> CalendarService:
    service = CalendarService(AsyncMock())
    service.pet_repo = AsyncMock()
    service.dose_repo = AsyncMock()
    service.medication_service = AsyncMock()
    return service


TEST_DAY = date(2026, 7, 8)


class TestCalendarServiceGetDay(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    @patch("app.services.calendar_service.cache_get", new_callable=AsyncMock)
    @patch("app.services.calendar_service.cache_set", new_callable=AsyncMock)
    async def test_cache_miss_queries_db_and_caches_result(
        self, mock_set: AsyncMock, mock_get: AsyncMock
    ) -> None:
        mock_get.return_value = None
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.get_doses_for_pet_day = AsyncMock(
            return_value=[_make_dose()]
        )

        result = await self.service.get_day(pet_id=1, owner_id=1, day=TEST_DAY)

        self.assertEqual(result.total, 1)
        self.assertEqual(result.pending, 1)
        mock_set.assert_awaited_once()

    @patch("app.services.calendar_service.cache_get", new_callable=AsyncMock)
    async def test_cache_hit_skips_db(self, mock_get: AsyncMock) -> None:
        mock_get.return_value = {
            "date": "2026-07-08", "pet_id": 1, "pet_name": "Барсик",
            "doses": [], "total": 0, "taken": 0, "pending": 0, "missed": 0,
        }

        result = await self.service.get_day(pet_id=1, owner_id=1, day=TEST_DAY)

        self.service.pet_repo.get_by_id.assert_not_called()
        self.assertEqual(result.total, 0)

    @patch("app.services.calendar_service.cache_get", new_callable=AsyncMock)
    async def test_pet_not_found_raises(self, mock_get: AsyncMock) -> None:
        mock_get.return_value = None
        self.service.pet_repo.get_by_id = AsyncMock(return_value=None)

        with self.assertRaises(NotFoundError):
            await self.service.get_day(pet_id=99, owner_id=1, day=TEST_DAY)

    @patch("app.services.calendar_service.cache_get", new_callable=AsyncMock)
    async def test_wrong_owner_raises(self, mock_get: AsyncMock) -> None:
        mock_get.return_value = None
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=999))

        with self.assertRaises(NotFoundError):
            await self.service.get_day(pet_id=1, owner_id=1, day=TEST_DAY)

    @patch("app.services.calendar_service.cache_get", new_callable=AsyncMock)
    @patch("app.services.calendar_service.cache_set", new_callable=AsyncMock)
    async def test_counters_calculated_correctly(
        self, _mock_set: AsyncMock, mock_get: AsyncMock
    ) -> None:
        mock_get.return_value = None
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        doses = [
            _make_dose(1, status=DoseStatus.TAKEN),
            _make_dose(2, status=DoseStatus.PENDING),
            _make_dose(3, status=DoseStatus.MISSED),
            _make_dose(4, status=DoseStatus.PENDING),
        ]
        self.service.dose_repo.get_doses_for_pet_day = AsyncMock(return_value=doses)

        result = await self.service.get_day(pet_id=1, owner_id=1, day=TEST_DAY)

        self.assertEqual(result.total, 4)
        self.assertEqual(result.taken, 1)
        self.assertEqual(result.pending, 2)
        self.assertEqual(result.missed, 1)


class TestCalendarServiceRecordDose(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_mark_taken_updates_status(self, mock_del: AsyncMock) -> None:
        dose = _make_dose(status=DoseStatus.PENDING)
        updated = _make_dose(status=DoseStatus.TAKEN)
        updated.taken_at = datetime.now(UTC)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.TAKEN
        action.taken_at = None
        action.notes = None

        result = await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        self.assertEqual(result.status, DoseStatus.TAKEN)
        mock_del.assert_awaited_once()

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_mark_skipped_with_notes(self, _mock_del: AsyncMock) -> None:
        dose = _make_dose(status=DoseStatus.PENDING)
        updated = _make_dose(status=DoseStatus.SKIPPED)
        updated.notes = "Отказался есть"
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.SKIPPED
        action.taken_at = None
        action.notes = "Отказался есть"

        result = await self.service.record_dose(dose_id=1, owner_id=1, data=action)
        self.assertEqual(result.status, DoseStatus.SKIPPED)

    async def test_dose_not_found_raises(self) -> None:
        self.service.dose_repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.record_dose(
                dose_id=999, owner_id=1, data=MagicMock()
            )

    async def test_wrong_pet_owner_raises_forbidden(self) -> None:
        dose = _make_dose()
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=999))

        with self.assertRaises(ForbiddenError):
            await self.service.record_dose(
                dose_id=1, owner_id=1, data=MagicMock()
            )

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_missed_triggers_extension(self, _mock_del: AsyncMock) -> None:
        dose = _make_dose(status=DoseStatus.PENDING)
        updated = _make_dose(status=DoseStatus.MISSED)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.MISSED
        action.taken_at = None
        action.notes = None

        await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        self.service.medication_service.extend_after_unresolved_dose.assert_awaited_once_with(
            dose.medication
        )

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_skipped_triggers_extension(self, _mock_del: AsyncMock) -> None:
        dose = _make_dose(status=DoseStatus.PENDING)
        updated = _make_dose(status=DoseStatus.SKIPPED)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.SKIPPED
        action.taken_at = None
        action.notes = None

        await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        self.service.medication_service.extend_after_unresolved_dose.assert_awaited_once()

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_taken_does_not_trigger_extension(self, _mock_del: AsyncMock) -> None:
        dose = _make_dose(status=DoseStatus.PENDING)
        updated = _make_dose(status=DoseStatus.TAKEN)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.TAKEN
        action.taken_at = None
        action.notes = None

        await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        self.service.medication_service.extend_after_unresolved_dose.assert_not_called()

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_re_saving_same_missed_status_does_not_re_trigger_extension(
        self, _mock_del: AsyncMock
    ) -> None:
        dose = _make_dose(status=DoseStatus.MISSED)
        updated = _make_dose(status=DoseStatus.MISSED)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet())
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.MISSED
        action.taken_at = None
        action.notes = "снова"

        await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        self.service.medication_service.extend_after_unresolved_dose.assert_not_called()

    @patch("app.services.calendar_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_cache_invalidated_for_correct_day(self, mock_del: AsyncMock) -> None:
        dose = _make_dose()
        dose.scheduled_at = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
        updated = _make_dose(status=DoseStatus.TAKEN)
        updated.taken_at = datetime.now(UTC)
        self.service.dose_repo.get_by_id = AsyncMock(return_value=dose)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet(pet_id=2))
        self.service.dose_repo.update_status = AsyncMock(return_value=updated)

        action = MagicMock()
        action.status = DoseStatus.TAKEN
        action.taken_at = None
        action.notes = None

        await self.service.record_dose(dose_id=1, owner_id=1, data=action)

        mock_del.assert_awaited_once_with("calendar:2:2026-07-10")


if __name__ == "__main__":
    unittest.main()
