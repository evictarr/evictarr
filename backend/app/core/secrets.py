"""Auto-generated, persisted-to-disk secrets.

SECRET_KEY (session cookie signing) and ENCRYPTION_KEY (Fernet key used to
encrypt TOTP secrets) don't need to be picked by the operator by hand - if
not supplied via env var, each is generated once and persisted as a file
under the config directory so it survives container restarts, then read
back on every subsequent start. An explicit env var, if set, always wins.
"""

import secrets
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet

_SECRET_KEY_FILENAME = ".secret_key"
_ENCRYPTION_KEY_FILENAME = ".encryption_key"


def _get_or_create(path: Path, generate: Callable[[], str]) -> str:
    if path.exists():
        return path.read_text().strip()

    value = generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    try:
        path.chmod(0o600)
    except OSError:
        # Best-effort - some volume drivers don't support chmod. The file
        # still works, just without the extra restriction.
        pass
    return value


def ensure_secret_key(config_dir: Path, provided: str | None) -> str:
    if provided:
        return provided
    return _get_or_create(config_dir / _SECRET_KEY_FILENAME, lambda: secrets.token_hex(32))


def ensure_encryption_key(config_dir: Path, provided: str | None) -> str:
    if provided:
        return provided
    return _get_or_create(config_dir / _ENCRYPTION_KEY_FILENAME, lambda: Fernet.generate_key().decode())
