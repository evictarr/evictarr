import httpx


class IntegrationError(Exception):
    """Raised whenever a call to an external service fails, with a message
    safe to show directly in the UI (test-connection results, run_events)."""


class BaseClient:
    """Thin async httpx wrapper shared by all four integration clients.
    Subclasses set default_headers() for their auth scheme and call
    _request() for everything else."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, headers=self._headers(), **kwargs)
        except httpx.RequestError as exc:
            raise IntegrationError(f"Could not reach {self._base_url}: {exc}") from exc

        if response.status_code == 401:
            raise IntegrationError("Authentication failed - check the API key")
        if response.status_code == 404:
            raise IntegrationError(f"Not found: {path}")
        if response.status_code >= 400:
            raise IntegrationError(f"Request to {path} failed with status {response.status_code}")
        return response

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("DELETE", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("PUT", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("POST", path, **kwargs)
