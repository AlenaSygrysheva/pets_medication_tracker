"""Unit tests for DrugService — repo is mocked."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.drug import Drug
from app.schemas.drug import DrugCreate, DrugUpdate
from app.services.drug_service import DrugService


def _make_drug(
    drug_id: int = 1,
    owner_id: int = 1,
    name: str = "Энроксил",
    strength: str = "15 мг",
    is_deleted: bool = False,
) -> Drug:
    d = MagicMock(spec=Drug)
    d.id = drug_id
    d.owner_id = owner_id
    d.name = name
    d.strength = strength
    d.purpose = "антибиотик"
    d.is_deleted = is_deleted
    return d


def _make_service() -> DrugService:
    service = DrugService(AsyncMock())
    service.repo = AsyncMock()
    return service


class TestDrugServiceGet(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    async def test_get_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.get_drug(drug_id=999, owner_id=1)

    async def test_get_deleted_raises_not_found(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_drug(is_deleted=True))
        with self.assertRaises(NotFoundError):
            await self.service.get_drug(drug_id=1, owner_id=1)

    async def test_get_wrong_owner_raises_forbidden(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_drug(owner_id=99))
        with self.assertRaises(ForbiddenError):
            await self.service.get_drug(drug_id=1, owner_id=1)

    async def test_get_success(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_drug(owner_id=7))
        result = await self.service.get_drug(drug_id=1, owner_id=7)
        self.assertEqual(result.id, 1)


class TestDrugServiceCreate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    async def test_create_new_drug_succeeds(self) -> None:
        self.service.repo.get_by_name_and_strength = AsyncMock(return_value=None)
        self.service.repo.create = AsyncMock(return_value=_make_drug())

        data = DrugCreate(name="Энроксил", purpose="антибиотик", strength="15 мг")
        result = await self.service.create_drug(owner_id=1, data=data)

        self.assertEqual(result.name, "Энроксил")
        self.service.repo.create.assert_awaited_once_with(1, data)

    async def test_create_duplicate_name_and_strength_raises_conflict(self) -> None:
        self.service.repo.get_by_name_and_strength = AsyncMock(
            return_value=_make_drug(name="Энроксил", strength="15 мг")
        )
        data = DrugCreate(name="Энроксил", purpose="антибиотик", strength="15 мг")
        with self.assertRaises(ConflictError):
            await self.service.create_drug(owner_id=1, data=data)

    async def test_same_name_different_strength_is_allowed(self) -> None:
        """"Энроксил 15 мг" and "Энроксил 25 мг" are different drugs."""
        self.service.repo.get_by_name_and_strength = AsyncMock(return_value=None)
        self.service.repo.create = AsyncMock(
            return_value=_make_drug(name="Энроксил", strength="25 мг")
        )

        data = DrugCreate(name="Энроксил", purpose="антибиотик", strength="25 мг")
        result = await self.service.create_drug(owner_id=1, data=data)

        self.assertEqual(result.strength, "25 мг")


class TestDrugServiceUpdate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    async def test_update_to_duplicate_name_and_strength_raises_conflict(self) -> None:
        drug = _make_drug(drug_id=1, name="Энроксил", strength="15 мг")
        other = _make_drug(drug_id=2, name="Байтрил", strength="25 мг")
        self.service.repo.get_by_id = AsyncMock(return_value=drug)
        self.service.repo.get_by_name_and_strength = AsyncMock(return_value=other)

        with self.assertRaises(ConflictError):
            await self.service.update_drug(
                drug_id=1, owner_id=1, data=DrugUpdate(name="Байтрил", strength="25 мг")
            )

    async def test_update_keeping_same_name_and_strength_is_allowed(self) -> None:
        drug = _make_drug(drug_id=1, name="Энроксил", strength="15 мг")
        self.service.repo.get_by_id = AsyncMock(return_value=drug)
        self.service.repo.get_by_name_and_strength = AsyncMock(return_value=drug)
        self.service.repo.update = AsyncMock(return_value=drug)

        await self.service.update_drug(
            drug_id=1, owner_id=1, data=DrugUpdate(purpose="новое описание")
        )

        self.service.repo.update.assert_awaited_once()


class TestDrugServiceDelete(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = _make_service()

    async def test_delete_blocked_while_active_course_exists(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_drug())
        self.service.repo.has_active_courses = AsyncMock(return_value=True)
        self.service.repo.soft_delete = AsyncMock()

        with self.assertRaises(ConflictError):
            await self.service.delete_drug(drug_id=1, owner_id=1)

        self.service.repo.soft_delete.assert_not_called()

    async def test_delete_allowed_when_no_active_courses(self) -> None:
        drug = _make_drug()
        self.service.repo.get_by_id = AsyncMock(return_value=drug)
        self.service.repo.has_active_courses = AsyncMock(return_value=False)
        self.service.repo.soft_delete = AsyncMock()

        await self.service.delete_drug(drug_id=1, owner_id=1)

        self.service.repo.soft_delete.assert_awaited_once_with(drug)

    async def test_delete_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.delete_drug(drug_id=999, owner_id=1)


if __name__ == "__main__":
    unittest.main()
