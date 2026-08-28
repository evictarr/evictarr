import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import *  # noqa: F401,F403  (registers models on Base.metadata)
from app.db.sqlite_pragmas import register_sqlite_pragmas

# NOTE: the target DB is SQLite. SQLite's ALTER TABLE only supports adding/
# renaming columns and tables - it can't retype a column or alter an
# existing CHECK/enum constraint in place. Any future migration that needs
# to do that must wrap the change in `op.batch_alter_table(...)`, which
# recreates the table under the hood, or it will fail against SQLite while
# working fine against Postgres.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    register_sqlite_pragmas(engine)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
