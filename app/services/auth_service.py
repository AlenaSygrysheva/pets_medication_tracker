import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.mailer import send_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        if await self.repo.get_by_email(data.email):
            raise ConflictError("Email already registered")
        if await self.repo.get_by_username(data.username):
            raise ConflictError("Username already taken")

        user = await self.repo.create(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        return self._build_tokens(user.id)

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        return self._build_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")
        user_id = int(payload["sub"])
        user = await self.repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")
        return self._build_tokens(user.id)

    async def forgot_password(self, email: str) -> None:
        """Always behaves the same regardless of whether the email is registered,
        so the endpoint can't be used to enumerate accounts."""
        user = await self.repo.get_by_email(email)
        if not user or not user.is_active:
            return

        raw_token, token_hash = generate_reset_token()
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        await self.repo.set_reset_token(user, token_hash, expires_at)

        reset_link = f"{settings.FRONTEND_URL}/?reset_token={raw_token}"
        body = (
            f"Здравствуйте, {user.username}!\n\n"
            "Вы (или кто-то другой) запросили восстановление пароля для аккаунта "
            "Pet Medication Tracker, привязанного к этому email.\n\n"
            f"Чтобы задать новый пароль, перейдите по ссылке (действительна "
            f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} минут):\n{reset_link}\n\n"
            "Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо."
        )
        await send_email(user.email, "Восстановление пароля — Pet Medication Tracker", body)
        logger.info("Password reset requested for user id=%d", user.id)

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = hash_reset_token(token)
        user = await self.repo.get_by_reset_token_hash(token_hash)
        expires_at = user.reset_token_expires_at if user else None
        # SQLite (used in tests) drops tzinfo on round-trip even for tz-aware columns;
        # everything we store here is UTC, so a naive value just needs it reattached.
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if not user or not expires_at or expires_at < datetime.now(UTC):
            raise BadRequestError("Invalid or expired reset token")

        await self.repo.update_password(user, hash_password(new_password))
        logger.info("Password reset completed for user id=%d", user.id)

    async def get_current_user(self, token: str) -> User:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise UnauthorizedError("Invalid access token")
        user = await self.repo.get_by_id(int(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")
        return user

    def _build_tokens(self, user_id: int) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
