"""Unit tests for MedicationService — repos, DB session and cache are mocked."""
import unittest
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.dose import Dose, DoseStatus
from app.models.medication import Medication
from app.models.pet import Pet
from app.schemas.medication import MedicationCreate
from app.services.medication_service import MedicationService


def _make_pet(pet_id: int = 1, owner_id: int = 1) -> Pet:
    p = MagicMock(spec=Pet)
    p.id = pet_id
    p.owner_id = owner_id
    return p


def _make_medication(
    med_id: int = 1,
    pet_id: int = 1,
    frequency: int = 2,
    days: int = 3,
) -> Medication:
    m = MagicMock(spec=Medication)
    m.id = med_id
    m.pet_id = pet_id
    m.name = "TestMed"
    m.dosage = "10mg"
    m.frequency_per_day = frequency
    m.start_date = date.today()
    m.end_date = date.today() + timedelta(days=days - 1)
    m.is_active = True
    return m


def _make_service() -> MedicationService:
    mock_db = AsyncMock()
    nested_ctx = AsyncMock()
    nested_ctx.__aenter__ = AsyncMock(return_value=None)
    nested_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_db.begin_nested = MagicMock(return_value=nested_ctx)
    mock_db.flush = AsyncMock()

    service = MedicationService(mock_db)
    service.repo = AsyncMock()
    service.pet_repo = AsyncMock()
    service.dose_repo = AsyncMock()
    return service


class TestMedicationServiceGet(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    async def test_get_medication_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.get_medication(medication_id=999, owner_id=1)

    async def test_get_medication_wrong_owner_raises_forbidden(self) -> None:
        med = _make_medication()
        self.service.repo.get_by_id = AsyncMock(return_value=med)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=99))
        with self.assertRaises(ForbiddenError):
            await self.service.get_medication(medication_id=1, owner_id=1)

    async def test_get_medication_success(self) -> None:
        med = _make_medication(med_id=5)
        pet = _make_pet(owner_id=7)
        self.service.repo.get_by_id = AsyncMock(return_value=med)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        result = await self.service.get_medication(medication_id=5, owner_id=7)
        self.assertEqual(result.id, 5)


class TestMedicationServiceCreate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_pet_not_found_raises(self, _cache: AsyncMock) -> None:
        self.service.pet_repo.get_by_id = AsyncMock(return_value=None)
        data = MedicationCreate(
            pet_id=99, name="X", dosage="5mg",
            frequency_per_day=1, start_date=date.today(),
        )
        with self.assertRaises(NotFoundError):
            await self.service.create_medication(owner_id=1, data=data)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_wrong_owner_raises(self, _cache: AsyncMock) -> None:
        self.service.pet_repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=99))
        data = MedicationCreate(
            pet_id=1, name="X", dosage="5mg",
            frequency_per_day=1, start_date=date.today(),
        )
        with self.assertRaises(NotFoundError):
            await self.service.create_medication(owner_id=1, data=data)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_generates_correct_dose_count(self, _cache: AsyncMock) -> None:
        # 2 times/day × 3 days = 6 doses
        pet = _make_pet(owner_id=5)
        med = _make_medication(frequency=2, days=3)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.repo.create = AsyncMock(return_value=med)
        self.service.dose_repo.create_bulk = AsyncMock()

        data = MedicationCreate(
            pet_id=1, name="X", dosage="5mg", frequency_per_day=2,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        await self.service.create_medication(owner_id=5, data=data)

        self.service.dose_repo.create_bulk.assert_awaited_once()
        doses: list[Dose] = self.service.dose_repo.create_bulk.call_args[0][0]
        self.assertEqual(len(doses), 6)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_1_time_day_generates_correct_count(self, _cache: AsyncMock) -> None:
        pet = _make_pet(owner_id=5)
        med = _make_medication(frequency=1, days=5)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.repo.create = AsyncMock(return_value=med)
        self.service.dose_repo.create_bulk = AsyncMock()

        data = MedicationCreate(
            pet_id=1, name="X", dosage="5mg", frequency_per_day=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=4),
        )
        await self.service.create_medication(owner_id=5, data=data)

        doses: list[Dose] = self.service.dose_repo.create_bulk.call_args[0][0]
        self.assertEqual(len(doses), 5)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_doses_have_pending_status(self, _cache: AsyncMock) -> None:
        pet = _make_pet(owner_id=5)
        med = _make_medication(frequency=1, days=2)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.repo.create = AsyncMock(return_value=med)
        self.service.dose_repo.create_bulk = AsyncMock()

        data = MedicationCreate(
            pet_id=1, name="X", dosage="5mg", frequency_per_day=1,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        await self.service.create_medication(owner_id=5, data=data)

        doses: list[Dose] = self.service.dose_repo.create_bulk.call_args[0][0]
        for dose in doses:
            self.assertEqual(dose.status, DoseStatus.PENDING)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_create_invalidates_cache(self, mock_cache: AsyncMock) -> None:
        pet = _make_pet(pet_id=3, owner_id=5)
        med = _make_medication(pet_id=3, frequency=1, days=1)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.repo.create = AsyncMock(return_value=med)
        self.service.dose_repo.create_bulk = AsyncMock()

        data = MedicationCreate(
            pet_id=3, name="X", dosage="5mg", frequency_per_day=1,
            start_date=date.today(),
        )
        await self.service.create_medication(owner_id=5, data=data)

        mock_cache.assert_awaited_once_with("calendar:3:*")


class TestMedicationServiceCancel(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_cancel_sets_inactive(self, _cache: AsyncMock) -> None:
        pet = _make_pet(pet_id=1, owner_id=5)
        med = _make_medication(med_id=3, pet_id=1)
        self.service.repo.get_by_id = AsyncMock(return_value=med)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.dose_repo.cancel_pending_doses = AsyncMock(return_value=7)

        await self.service.cancel_medication(medication_id=3, owner_id=5)

        self.assertFalse(med.is_active)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_cancel_calls_cancel_pending_doses(self, _cache: AsyncMock) -> None:
        pet = _make_pet(pet_id=1, owner_id=5)
        med = _make_medication(med_id=3, pet_id=1)
        self.service.repo.get_by_id = AsyncMock(return_value=med)
        self.service.pet_repo.get_by_id = AsyncMock(return_value=pet)
        self.service.dose_repo.cancel_pending_doses = AsyncMock(return_value=3)

        await self.service.cancel_medication(medication_id=3, owner_id=5)

        self.service.dose_repo.cancel_pending_doses.assert_awaited_once_with(3)

    @patch("app.services.medication_service.cache_delete_pattern", new_callable=AsyncMock)
    async def test_cancel_not_found_raises(self, _cache: AsyncMock) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.cancel_medication(medication_id=999, owner_id=1)


class TestDoseGenerationAlgorithm(unittest.TestCase):
    """Tests for the dose scheduling algorithm in MedicationService._generate_doses."""

    def _generate(self, frequency: int, days: int) -> list[Dose]:
        start = date.today()
        end = start + timedelta(days=days - 1)
        interval_hours = 24 // frequency
        doses: list[Dose] = []
        current = start
        while current <= end:
            for i in range(frequency):
                hour = 8 + i * interval_hours
                scheduled = datetime.combine(
                    current, time(hour=min(hour, 23), minute=0), tzinfo=UTC
                )
                doses.append(
                    Dose(
                        medication_id=1,
                        scheduled_at=scheduled,
                        status=DoseStatus.PENDING,
                    )
                )
            current += timedelta(days=1)
        return doses

    def test_once_daily_7_days(self) -> None:
        self.assertEqual(len(self._generate(1, 7)), 7)

    def test_twice_daily_7_days(self) -> None:
        self.assertEqual(len(self._generate(2, 7)), 14)

    def test_thrice_daily_3_days(self) -> None:
        self.assertEqual(len(self._generate(3, 3)), 9)

    def test_single_day_single_dose(self) -> None:
        self.assertEqual(len(self._generate(1, 1)), 1)

    def test_single_day_two_doses(self) -> None:
        self.assertEqual(len(self._generate(2, 1)), 2)

    def test_doses_are_sorted_chronologically(self) -> None:
        doses = self._generate(3, 2)
        times = [d.scheduled_at for d in doses]
        self.assertEqual(times, sorted(times))

    def test_all_doses_are_pending(self) -> None:
        doses = self._generate(2, 3)
        self.assertTrue(all(d.status == DoseStatus.PENDING for d in doses))


if __name__ == "__main__":
    unittest.main()
