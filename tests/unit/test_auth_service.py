"""Unit tests for AuthService — all DB calls are mocked."""
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User
from app.services.auth_service import AuthService


def _make_user(
    user_id: int = 1,
    email: str = "u@test.com",
    username: str = "testuser",
    hashed_pw: str = "",
    is_active: bool = True,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.username = username
    user.hashed_password = hashed_pw
    user.is_active = is_active
    return user


class TestAuthServiceRegister(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AuthService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_register_returns_tokens(self) -> None:
        self.service.repo.get_by_email = AsyncMock(return_value=None)
        self.service.repo.get_by_username = AsyncMock(return_value=None)
        self.service.repo.create = AsyncMock(return_value=_make_user(user_id=1))

        result = await self.service.register(
            MagicMock(email="new@test.com", username="newuser", password="pass1234")
        )
        self.assertIn("access_token", result.model_dump())
        self.assertIn("refresh_token", result.model_dump())

    async def test_register_duplicate_email_raises_conflict(self) -> None:
        self.service.repo.get_by_email = AsyncMock(return_value=_make_user())

        with self.assertRaises(ConflictError):
            await self.service.register(
                MagicMock(email="dup@test.com", username="other", password="pass1234")
            )

    async def test_register_duplicate_username_raises_conflict(self) -> None:
        self.service.repo.get_by_email = AsyncMock(return_value=None)
        self.service.repo.get_by_username = AsyncMock(return_value=_make_user())

        with self.assertRaises(ConflictError):
            await self.service.register(
                MagicMock(email="unique@test.com", username="taken", password="pass1234")
            )


class TestAuthServiceLogin(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AuthService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_login_correct_credentials_returns_tokens(self) -> None:
        hashed = hash_password("password123")
        self.service.repo.get_by_email = AsyncMock(
            return_value=_make_user(hashed_pw=hashed)
        )

        result = await self.service.login(
            MagicMock(email="u@test.com", password="password123")
        )
        self.assertIn("access_token", result.model_dump())

    async def test_login_wrong_password_raises_unauthorized(self) -> None:
        hashed = hash_password("correct")
        self.service.repo.get_by_email = AsyncMock(return_value=_make_user(hashed_pw=hashed))

        with self.assertRaises(UnauthorizedError):
            await self.service.login(MagicMock(email="u@test.com", password="wrong"))

    async def test_login_user_not_found_raises_unauthorized(self) -> None:
        self.service.repo.get_by_email = AsyncMock(return_value=None)

        with self.assertRaises(UnauthorizedError):
            await self.service.login(MagicMock(email="ghost@test.com", password="pass"))

    async def test_login_inactive_user_raises_unauthorized(self) -> None:
        hashed = hash_password("password")
        self.service.repo.get_by_email = AsyncMock(
            return_value=_make_user(hashed_pw=hashed, is_active=False)
        )

        with self.assertRaises(UnauthorizedError):
            await self.service.login(MagicMock(email="u@test.com", password="password"))


class TestAuthServiceTokens(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AuthService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_get_current_user_valid_access_token(self) -> None:
        mock_user = _make_user(user_id=5)
        self.service.repo.get_by_id = AsyncMock(return_value=mock_user)

        user = await self.service.get_current_user(create_access_token(5))
        self.assertEqual(user.id, 5)

    async def test_get_current_user_invalid_token_raises(self) -> None:
        with self.assertRaises(UnauthorizedError):
            await self.service.get_current_user("bad.token")

    async def test_get_current_user_refresh_token_raises(self) -> None:
        with self.assertRaises(UnauthorizedError):
            await self.service.get_current_user(create_refresh_token(1))

    async def test_refresh_valid_token_returns_new_tokens(self) -> None:
        mock_user = _make_user(user_id=3)
        self.service.repo.get_by_id = AsyncMock(return_value=mock_user)

        result = await self.service.refresh(create_refresh_token(3))
        self.assertIn("access_token", result.model_dump())

    async def test_refresh_access_token_instead_of_refresh_raises(self) -> None:
        with self.assertRaises(UnauthorizedError):
            await self.service.refresh(create_access_token(1))

    async def test_refresh_invalid_token_raises(self) -> None:
        with self.assertRaises(UnauthorizedError):
            await self.service.refresh("not.a.token")


if __name__ == "__main__":
    unittest.main()
