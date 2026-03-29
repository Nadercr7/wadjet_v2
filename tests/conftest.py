"""Shared test fixtures for Wadjet v3 Beta."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test settings BEFORE any app imports
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-do-not-use-in-production")
os.environ.setdefault("CSRF_SECRET", "test-csrf-secret-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.config import Settings
from app.db.database import Base, get_db
from app.db.models import User
from app.main import create_app
from app.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the rate limiter storage before each test to avoid 429s."""
    limiter.reset()
    yield


@pytest.fixture()
def mock_settings() -> Settings:
    """Return Settings with known test values."""
    return Settings(
        environment="development",
        jwt_secret="test-jwt-secret-do-not-use-in-production",
        csrf_secret="test-csrf-secret-do-not-use-in-production",
        database_url="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture()
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory SQLite DB per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture()
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to a fresh test DB."""
    app = create_app()

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
async def authenticated_client(
    test_db: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with a valid auth token for a pre-created test user."""
    # Create test user directly in DB
    user = User(
        id="test-user-id",
        email="test@wadjet.app",
        password_hash=hash_password("TestPass123"),
        display_name="Test User",
    )
    test_db.add(user)
    await test_db.commit()

    # Create access token
    token = create_access_token("test-user-id")

    app = create_app()

    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        # Fetch a page to get the CSRF cookie, then set it as header for all future requests
        await client.get("/api/health")
        csrf_token = client.cookies.get("csrftoken")
        if csrf_token:
            client.headers["x-csrftoken"] = csrf_token
        yield client

    app.dependency_overrides.clear()
