from app.integrations.base_client import BaseClient


class RadarrClient(BaseClient):
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        super().__init__(base_url, timeout)
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key}

    async def test_connection(self) -> str:
        response = await self.get("/api/v3/system/status")
        data = response.json()
        return f"Connected to Radarr {data.get('version', '?')}"

    async def get_movies(self) -> list[dict]:
        response = await self.get("/api/v3/movie")
        return response.json()

    async def delete_movie(self, movie_id: int, delete_files: bool = True) -> None:
        """Deletes the movie record from Radarr. With delete_files=True this also
        removes the file(s) from disk and implicitly stops monitoring - Evictarr
        never issues a raw filesystem delete itself."""
        await self.delete(
            f"/api/v3/movie/{movie_id}",
            params={"deleteFiles": str(delete_files).lower(), "addImportExclusion": "false"},
        )

    async def get_tracked_file_paths(self) -> set[str]:
        movies = await self.get_movies()
        return {m["movieFile"]["path"] for m in movies if m.get("hasFile") and m.get("movieFile")}


def find_by_tmdb_id(movies: list[dict], tmdb_id: str) -> dict | None:
    for movie in movies:
        if str(movie.get("tmdbId")) == str(tmdb_id):
            return movie
    return None
