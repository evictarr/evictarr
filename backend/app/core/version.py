import tomllib
from functools import lru_cache
from pathlib import Path

# backend/app/core/version.py -> backend/pyproject.toml. Read directly from
# pyproject.toml (not importlib.metadata) so this can never drift from an
# editable/dev install's stale package metadata - pyproject.toml is the one
# place version already gets bumped on release.
_PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


@lru_cache
def get_app_version() -> str:
    with _PYPROJECT_PATH.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]
