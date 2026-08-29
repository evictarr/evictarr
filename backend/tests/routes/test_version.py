import tomllib
from pathlib import Path

_PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


async def test_version_matches_pyproject(client):
    with _PYPROJECT_PATH.open("rb") as f:
        expected = tomllib.load(f)["project"]["version"]

    response = await client.get("/api/version")

    assert response.status_code == 200
    assert response.json() == {"version": expected}
