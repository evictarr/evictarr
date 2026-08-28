from app.integrations.base_client import BaseClient


class SonarrClient(BaseClient):
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        super().__init__(base_url, timeout)
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key}

    async def test_connection(self) -> str:
        response = await self.get("/api/v3/system/status")
        data = response.json()
        return f"Connected to Sonarr {data.get('version', '?')}"

    async def get_series(self) -> list[dict]:
        response = await self.get("/api/v3/series")
        return response.json()

    async def get_series_by_id(self, series_id: int) -> dict:
        response = await self.get(f"/api/v3/series/{series_id}")
        return response.json()

    async def get_episode_files(self, series_id: int) -> list[dict]:
        response = await self.get("/api/v3/episodefile", params={"seriesId": series_id})
        return response.json()

    async def delete_series(self, series_id: int, delete_files: bool = True) -> None:
        """Deletes the whole series record from Sonarr, files and all."""
        await self.delete(f"/api/v3/series/{series_id}", params={"deleteFiles": str(delete_files).lower()})

    async def unmonitor_season(self, series_id: int, season_number: int) -> None:
        series = await self.get_series_by_id(series_id)
        for season in series.get("seasons", []):
            if season.get("seasonNumber") == season_number:
                season["monitored"] = False
        await self.put(f"/api/v3/series/{series_id}", json=series)

    async def delete_season_files(self, series_id: int, season_number: int) -> None:
        """Deletes only the episode files belonging to one season - used for
        season-granularity cleanup, leaving the rest of the series untouched."""
        files = await self.get_episode_files(series_id)
        for f in files:
            if f.get("seasonNumber") == season_number:
                await self.delete(f"/api/v3/episodefile/{f['id']}")

    async def get_tracked_file_paths(self) -> set[str]:
        all_series = await self.get_series()
        paths: set[str] = set()
        for series in all_series:
            files = await self.get_episode_files(series["id"])
            paths.update(f["path"] for f in files if f.get("path"))
        return paths


def find_by_tvdb_id(series_list: list[dict], tvdb_id: str) -> dict | None:
    for series in series_list:
        if str(series.get("tvdbId")) == str(tvdb_id):
            return series
    return None
