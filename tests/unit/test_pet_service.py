"""Unit tests for PetService — repository is mocked."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.pet import Pet
from app.schemas.pet import PetCreate, PetUpdate
from app.services.pet_service import PetService


def _make_pet(
    pet_id: int = 1,
    owner_id: int = 1,
    name: str = "Барсик",
    avatar_path: str | None = None,
) -> Pet:
    pet = MagicMock(spec=Pet)
    pet.id = pet_id
    pet.owner_id = owner_id
    pet.name = name
    pet.avatar_path = avatar_path
    return pet


class TestPetServiceGet(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = PetService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_get_pets_returns_all_owner_pets(self) -> None:
        self.service.repo.get_all_by_owner = AsyncMock(
            return_value=[_make_pet(1, 10), _make_pet(2, 10)]
        )
        result = await self.service.get_pets(owner_id=10)
        self.assertEqual(len(result), 2)
        self.service.repo.get_all_by_owner.assert_awaited_once_with(10)

    async def test_get_pets_empty_list(self) -> None:
        self.service.repo.get_all_by_owner = AsyncMock(return_value=[])
        result = await self.service.get_pets(owner_id=99)
        self.assertEqual(result, [])

    async def test_get_pet_success(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_pet(pet_id=1, owner_id=5))
        result = await self.service.get_pet(pet_id=1, owner_id=5)
        self.assertEqual(result.id, 1)

    async def test_get_pet_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.get_pet(pet_id=999, owner_id=1)

    async def test_get_pet_wrong_owner_raises_forbidden(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=999))
        with self.assertRaises(ForbiddenError):
            await self.service.get_pet(pet_id=1, owner_id=1)


class TestPetServiceCreate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = PetService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_create_calls_repo_and_returns_pet(self) -> None:
        new_pet = _make_pet(pet_id=7, owner_id=3)
        self.service.repo.create = AsyncMock(return_value=new_pet)
        data = PetCreate(name="Котик", species="cat")

        result = await self.service.create_pet(owner_id=3, data=data)

        self.service.repo.create.assert_awaited_once_with(3, data)
        self.assertEqual(result.id, 7)

    async def test_create_passes_correct_owner(self) -> None:
        self.service.repo.create = AsyncMock(return_value=_make_pet(owner_id=42))
        data = PetCreate(name="X", species="dog")
        await self.service.create_pet(owner_id=42, data=data)
        call_args = self.service.repo.create.call_args
        self.assertEqual(call_args[0][0], 42)


class TestPetServiceUpdate(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = PetService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_update_pet_success(self) -> None:
        original = _make_pet(pet_id=1, owner_id=2, name="Шарик")
        updated = _make_pet(pet_id=1, owner_id=2, name="Мурзик")
        self.service.repo.get_by_id = AsyncMock(return_value=original)
        self.service.repo.update = AsyncMock(return_value=updated)

        result = await self.service.update_pet(
            pet_id=1, owner_id=2, data=PetUpdate(name="Мурзик")
        )
        self.assertEqual(result.name, "Мурзик")

    async def test_update_pet_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.update_pet(
                pet_id=999, owner_id=1, data=PetUpdate(name="X")
            )

    async def test_update_pet_wrong_owner_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=50))
        with self.assertRaises(ForbiddenError):
            await self.service.update_pet(
                pet_id=1, owner_id=1, data=PetUpdate(name="X")
            )


class TestPetServiceDelete(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = PetService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_delete_pet_calls_repo_delete(self) -> None:
        pet = _make_pet(pet_id=1, owner_id=1, avatar_path=None)
        self.service.repo.get_by_id = AsyncMock(return_value=pet)
        self.service.repo.delete = AsyncMock()

        await self.service.delete_pet(pet_id=1, owner_id=1)

        self.service.repo.delete.assert_awaited_once_with(pet)

    async def test_delete_pet_not_found_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=None)
        with self.assertRaises(NotFoundError):
            await self.service.delete_pet(pet_id=999, owner_id=1)

    async def test_delete_pet_wrong_owner_raises(self) -> None:
        self.service.repo.get_by_id = AsyncMock(return_value=_make_pet(owner_id=99))
        with self.assertRaises(ForbiddenError):
            await self.service.delete_pet(pet_id=1, owner_id=1)


if __name__ == "__main__":
    unittest.main()
