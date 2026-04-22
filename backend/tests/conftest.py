"""
Shared pytest fixtures for the Multilingual Sentiment Dashboard test suite.

Test strategy
─────────────
• A dedicated test PostgreSQL database is used (sentimentdb_test).
  The DATABASE_URL env var is overridden via TEST_DATABASE_URL or defaults
  to the dev DB URL with the database name replaced.
• Redis is mocked globally — tests never require a running Redis instance.
• External AI calls (Claude, ChromaDB) are mocked per-test where needed.
• Each test function gets a fresh DB session that rolls back after the test.
• Three auth fixtures provide Bearer tokens for admin, analyst and viewer roles.
"""

import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from unittest.mock import AsyncMock, MagicMock, patch

# ── Test database URL ──────────────────────────────────────────────────────────
_default_db = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://sentimentuser:sentimentpass@localhost:5432/sentimentdb",
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    _default_db.replace("/sentimentdb", "/sentimentdb_test"),
)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Session-scoped engine & schema ────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test DB schema once per session; drop it on teardown."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Import all models so Base knows about them
        import app.models.audit_log   # noqa: F401
        import app.models.human_review  # noqa: F401
        import app.models.review       # noqa: F401
        import app.models.alert        # noqa: F401
        import app.models.user         # noqa: F401
        import app.models.tenant       # noqa: F401
        from app.core.database import Base
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        from app.core.database import Base
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Per-test session with automatic rollback ──────────────────────────────────

@pytest_asyncio.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session that rolls back after each test (keeps tests isolated)."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ── HTTP client with mocked Redis lifespan ────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with DB overridden to the test session."""
    from app.main import app
    from app.core.database import get_db

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db

    # Mock Redis so tests never require a running Redis
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)

    with (
        patch("app.core.redis._redis_client", mock_redis),
        patch("app.core.redis.get_redis", AsyncMock(return_value=mock_redis)),
        patch("app.core.redis.close_redis", AsyncMock()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

async def _create_user(db: AsyncSession, *, role: str, email: str, tenant_id: str) -> dict:
    from app.models.user import User

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=email,
        full_name=f"Test {role.capitalize()}",
        hashed_password=pwd_ctx.hash("Test@Password1"),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": email, "password": "Test@Password1", "role": role}


async def _get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ── Tenant fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant(db: AsyncSession):
    from app.models.tenant import Tenant

    t = Tenant(id=str(uuid.uuid4()), name="Acme Corp", slug=f"acme-{uuid.uuid4().hex[:6]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ── Role fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db, tenant):
    return await _create_user(db, role="admin", email=f"admin-{uuid.uuid4().hex[:6]}@test.com", tenant_id=tenant.id)


@pytest_asyncio.fixture
async def analyst_user(db, tenant):
    return await _create_user(db, role="analyst", email=f"analyst-{uuid.uuid4().hex[:6]}@test.com", tenant_id=tenant.id)


@pytest_asyncio.fixture
async def viewer_user(db, tenant):
    return await _create_user(db, role="viewer", email=f"viewer-{uuid.uuid4().hex[:6]}@test.com", tenant_id=tenant.id)


# ── Token fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    return await _get_token(client, admin_user["email"], admin_user["password"])


@pytest_asyncio.fixture
async def analyst_token(client, analyst_user):
    return await _get_token(client, analyst_user["email"], analyst_user["password"])


@pytest_asyncio.fixture
async def viewer_token(client, viewer_user):
    return await _get_token(client, viewer_user["email"], viewer_user["password"])


def auth(token: str) -> dict:
    """Shorthand to build Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
