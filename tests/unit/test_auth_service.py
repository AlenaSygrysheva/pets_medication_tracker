"""Unit tests for AuthService — all DB calls are mocked."""
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
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
    user.reset_token_hash = None
    user.reset_token_expires_at = None
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


class TestAuthServiceForgotPassword(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AuthService(AsyncMock())
        self.service.repo = AsyncMock()

    @patch("app.services.auth_service.send_email", new_callable=AsyncMock)
    async def test_unknown_email_sends_nothing(self, mock_send: AsyncMock) -> None:
        self.service.repo.get_by_email = AsyncMock(return_value=None)

        await self.service.forgot_password("ghost@test.com")

        mock_send.assert_not_called()
        self.service.repo.set_reset_token.assert_not_called()

    @patch("app.services.auth_service.send_email", new_callable=AsyncMock)
    async def test_inactive_user_sends_nothing(self, mock_send: AsyncMock) -> None:
        user = _make_user(is_active=False)
        self.service.repo.get_by_email = AsyncMock(return_value=user)

        await self.service.forgot_password(user.email)

        mock_send.assert_not_called()
        self.service.repo.set_reset_token.assert_not_called()

    @patch("app.services.auth_service.send_email", new_callable=AsyncMock)
    async def test_known_email_sets_token_and_sends_email(self, mock_send: AsyncMock) -> None:
        user = _make_user(user_id=7, email="u@test.com")
        self.service.repo.get_by_email = AsyncMock(return_value=user)

        await self.service.forgot_password("u@test.com")

        self.service.repo.set_reset_token.assert_awaited_once()
        set_args = self.service.repo.set_reset_token.call_args[0]
        self.assertEqual(set_args[0], user)
        mock_send.assert_awaited_once()
        self.assertEqual(mock_send.call_args[0][0], "u@test.com")


class TestAuthServiceResetPassword(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = AuthService(AsyncMock())
        self.service.repo = AsyncMock()

    async def test_unknown_token_raises(self) -> None:
        self.service.repo.get_by_reset_token_hash = AsyncMock(return_value=None)
        with self.assertRaises(BadRequestError):
            await self.service.reset_password("bad-token", "newpassword123")

    async def test_expired_token_raises(self) -> None:
        user = _make_user()
        user.reset_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        self.service.repo.get_by_reset_token_hash = AsyncMock(return_value=user)

        with self.assertRaises(BadRequestError):
            await self.service.reset_password("some-token", "newpassword123")

        self.service.repo.update_password.assert_not_called()

    async def test_valid_token_updates_password(self) -> None:
        user = _make_user()
        user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        self.service.repo.get_by_reset_token_hash = AsyncMock(return_value=user)

        await self.service.reset_password("some-token", "newpassword123")

        self.service.repo.update_password.assert_awaited_once()
        self.assertEqual(self.service.repo.update_password.call_args[0][0], user)


if __name__ == "__main__":
    unittest.main()
