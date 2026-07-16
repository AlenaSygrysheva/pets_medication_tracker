import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncSession:  # type: ignore[override]
    async with TestSessionLocal() as session:
        try:
            yield session  # type: ignore[misc]
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:  # type: ignore[override]
    loop = asyncio.new_event_loop()
    yield loop  # type: ignore[misc]
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db() -> None:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # type: ignore[misc]
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def mock_redis() -> None:  # type: ignore[misc]
    """Mock all Redis cache calls so integration tests need no running Redis."""
    with (
        patch(
            "app.services.calendar_service.cache_get",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("app.services.calendar_service.cache_set", new_callable=AsyncMock),
        patch(
            "app.services.calendar_service.cache_delete_pattern",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.medication_service.cache_delete_pattern",
            new_callable=AsyncMock,
        ),
    ):
        yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac  # type: ignore[misc]


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
        },
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    token: str = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
