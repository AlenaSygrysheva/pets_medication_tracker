
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_reset_token_hash(self, token_hash: str) -> User | None:
        result = await self.db.execute(select(User).where(User.reset_token_hash == token_hash))
        return result.scalar_one_or_none()

    async def create(self, email: str, username: str, hashed_password: str) -> User:
        user = User(email=email, username=username, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def set_reset_token(
        self, user: User, token_hash: str, expires_at: datetime
    ) -> None:
        user.reset_token_hash = token_hash
        user.reset_token_expires_at = expires_at
        await self.db.flush()

    async def update_password(self, user: User, hashed_password: str) -> None:
        user.hashed_password = hashed_password
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        await self.db.flush()
