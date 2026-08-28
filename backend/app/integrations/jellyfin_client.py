from datetime import datetime

from app.integrations.base_client import BaseClient

_ITEM_FIELDS = "ProviderIds,UserData"


class JellyfinClient(BaseClient):
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        super().__init__(base_url, timeout)
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-Emby-Token": self._api_key}

    async def test_connection(self) -> str:
        response = await self.get("/System/Info")
        data = response.json()
        return f"Connected to {data.get('ServerName', 'Jellyfin')} (version {data.get('Version', '?')})"

    async def list_users(self) -> list[dict]:
        response = await self.get("/Users")
        return [{"id": u["Id"], "name": u["Name"]} for u in response.json()]

    async def get_movies(self, user_id: str) -> list[dict]:
        response = await self.get(
            f"/Users/{user_id}/Items",
            params={
                "IncludeItemTypes": "Movie",
                "Recursive": "true",
                "Fields": _ITEM_FIELDS,
            },
        )
        return response.json().get("Items", [])

    async def get_series(self, user_id: str) -> list[dict]:
        response = await self.get(
            f"/Users/{user_id}/Items",
            params={
                "IncludeItemTypes": "Series",
                "Recursive": "true",
                "Fields": _ITEM_FIELDS,
            },
        )
        return response.json().get("Items", [])

    async def get_seasons(self, user_id: str, series_id: str) -> list[dict]:
        response = await self.get(
            f"/Shows/{series_id}/Seasons",
            params={"userId": user_id, "Fields": _ITEM_FIELDS},
        )
        return response.json().get("Items", [])


def parse_last_played(item: dict) -> datetime | None:
    raw = item.get("UserData", {}).get("LastPlayedDate")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_played(item: dict) -> bool:
    return bool(item.get("UserData", {}).get("Played"))


def is_favorite(item: dict) -> bool:
    return bool(item.get("UserData", {}).get("IsFavorite"))


def play_count(item: dict) -> int:
    return int(item.get("UserData", {}).get("PlayCount") or 0)


def tmdb_id(item: dict) -> str | None:
    return item.get("ProviderIds", {}).get("Tmdb")


def tvdb_id(item: dict) -> str | None:
    return item.get("ProviderIds", {}).get("Tvdb")
