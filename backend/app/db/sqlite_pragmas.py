from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


def register_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Enable WAL mode + a busy timeout on every new SQLite connection.

    The app runs a shared APScheduler (daily scan + grace-period executor)
    alongside regular web requests, all against a single on-disk file. WAL
    mode lets readers proceed concurrently with a writer, and busy_timeout
    makes a connection that does hit writer contention retry for a few
    seconds instead of failing immediately with "database is locked".
    Also enables foreign key enforcement, which SQLite disables by default
    per-connection (unlike Postgres, which always enforces it).

    No-op for any other dialect, so it's safe to call unconditionally.
    """
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
