from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenError
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await AuthService(db).get_current_user(credentials.credentials)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not settings.ADMIN_EMAIL or current_user.email.lower() != settings.ADMIN_EMAIL.lower():
        raise ForbiddenError("Admin access required")
    return current_user
