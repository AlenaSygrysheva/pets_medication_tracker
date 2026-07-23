import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(  # type: ignore[no-any-return]
        {"sub": str(subject), "exp": expire, "type": "access"}, settings.SECRET_KEY, settings.ALGORITHM
    )


def create_refresh_token(subject: int) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(  # type: ignore[no-any-return]
        {"sub": str(subject), "exp": expire, "type": "refresh"}, settings.SECRET_KEY, settings.ALGORITHM
    )


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])  # type: ignore[no-any-return]
    except JWTError:
        return None


def generate_reset_token() -> tuple[str, str]:
    """Returns (raw_token_for_the_email_link, sha256_hash_to_store_in_the_db)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
