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

    async def get_episodes(self, user_id: str, series_id: str, season_id: str | None = None) -> list[dict]:
        params = {"userId": user_id, "Fields": _ITEM_FIELDS}
        if season_id is not None:
            params["seasonId"] = season_id
        response = await self.get(f"/Shows/{series_id}/Episodes", params=params)
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


def latest_played_at(items: list[dict]) -> datetime | None:
    """Max LastPlayedDate across a list of items (e.g. a season/series'
    episodes). Jellyfin never stamps LastPlayedDate on a Season or Series
    item itself - only on the leaf item actually played (episode/movie) -
    so a season/series "watched at" timestamp has to be aggregated from its
    episodes instead of read off the folder item directly."""
    dates = [d for d in (parse_last_played(i) for i in items) if d is not None]
    return max(dates) if dates else None


def is_favorite(item: dict) -> bool:
    return bool(item.get("UserData", {}).get("IsFavorite"))


def play_count(item: dict) -> int:
    return int(item.get("UserData", {}).get("PlayCount") or 0)


def tmdb_id(item: dict) -> str | None:
    return item.get("ProviderIds", {}).get("Tmdb")


def tvdb_id(item: dict) -> str | None:
    return item.get("ProviderIds", {}).get("Tvdb")
