from app.integrations.base_client import BaseClient


class SeerrClient(BaseClient):
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        super().__init__(base_url, timeout)
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key}

    async def test_connection(self) -> str:
        response = await self.get("/api/v1/settings/main")
        data = response.json()
        return f"Connected to {data.get('applicationTitle', 'Seerr')}"

    async def list_requests(self, filter: str = "available", take: int = 50) -> list[dict]:
        """filter matches Seerr's own request filters, e.g. 'available', 'approved', 'pending'."""
        results: list[dict] = []
        skip = 0
        while True:
            response = await self.get(
                "/api/v1/request", params={"filter": filter, "take": take, "skip": skip, "sort": "added"}
            )
            page = response.json()
            results.extend(page.get("results", []))
            page_info = page.get("pageInfo", {})
            skip += take
            if skip >= page_info.get("results", 0):
                break
        return results

    async def delete_request(self, request_id: int) -> None:
        await self.delete(f"/api/v1/request/{request_id}")

    async def get_tv_details(self, tmdb_id: str) -> dict:
        """Seerr's TV-details endpoint proxies TMDB metadata for any show by
        TMDB id, independent of whether it was ever requested - used to find
        out how many episodes a season is actually supposed to have."""
        response = await self.get(f"/api/v1/tv/{tmdb_id}")
        return response.json()


def media_tmdb_id(request: dict) -> str | None:
    tmdb_id = request.get("media", {}).get("tmdbId")
    return str(tmdb_id) if tmdb_id is not None else None


def media_tvdb_id(request: dict) -> str | None:
    tvdb_id = request.get("media", {}).get("tvdbId")
    return str(tvdb_id) if tvdb_id is not None else None


def media_type(request: dict) -> str | None:
    return request.get("media", {}).get("mediaType")


def media_added_at(request: dict) -> str | None:
    return request.get("media", {}).get("mediaAddedAt")


def season_episode_count(tv_details: dict, season_number: int) -> int | None:
    """TMDB's expected episode count for one season of a show, as proxied by
    Seerr's TV-details response. `None` if the season isn't listed at all
    (unknown show, bad season number) or its count wasn't reported."""
    for season in tv_details.get("seasons", []):
        if season.get("seasonNumber") == season_number:
            count = season.get("episodeCount")
            return count if isinstance(count, int) and count > 0 else None
    return None
