from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.db.sqlite_pragmas import register_sqlite_pragmas


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
register_sqlite_pragmas(engine)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
