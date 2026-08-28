from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import ensure_encryption_key, ensure_secret_key


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///dev.db"

    # Directory used to persist auto-generated secrets (see app/core/secrets.py).
    # Docker sets this to /config, the same volume the SQLite db lives in.
    config_dir: str = "."

    # Left unset by default - auto-generated and persisted under config_dir
    # on first run. Set explicitly to pin them instead (e.g. to share one
    # key across a manual multi-instance setup).
    secret_key: str | None = None
    encryption_key: str | None = None

    session_cookie_secure: bool = True
    session_max_age_hours: int = 24 * 14

    timezone: str = "UTC"
    log_level: str = "INFO"

    # Read-only mounts matching the paths Radarr/Sonarr already use - only
    # ever read, never written to. Used solely by the orphaned-file scan.
    movies_library_path: str = "/movies"
    tv_library_path: str = "/shows"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    config_dir = Path(settings.config_dir)
    settings.secret_key = ensure_secret_key(config_dir, settings.secret_key)
    settings.encryption_key = ensure_encryption_key(config_dir, settings.encryption_key)
    return settings
