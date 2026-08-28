# backend/tests/conftest.py
#
# IMPORTANT: the env vars below MUST be set before anything imports
# app.core.config/app.db.base - get_settings() is @lru_cache'd and the
# SQLAlchemy engine is created at module-import time, so if any `app.*`
# import happens above these lines, tests will silently point at your
# real dev database instead of a throwaway one. Keep these three lines
# first in this file.
import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="evictarr-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_tmp_dir, 'test.db').as_posix()}"
os.environ["CONFIG_DIR"] = _tmp_dir
os.environ["SESSION_COOKIE_SECURE"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient

from app.bootstrap import ensure_app_settings
from app.db.base import Base, async_session_factory, engine, get_db
from app.main import app


@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        # Normally seeded by app.main's lifespan on real startup - that
        # never runs under ASGITransport, so seed it here instead.
        await ensure_app_settings(session)
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
