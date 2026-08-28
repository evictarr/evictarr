import httpx


class NotificationError(Exception):
    pass


class NotificationProvider:
    async def send(self, message: str) -> None:
        raise NotImplementedError


async def _post(url: str, json: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=json)
    except httpx.RequestError as exc:
        raise NotificationError(f"Could not reach {url}: {exc}") from exc
    if response.status_code >= 400:
        raise NotificationError(f"Request failed with status {response.status_code}: {response.text[:200]}")
