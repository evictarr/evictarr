from app.notifications.base import NotificationProvider, _post


class DiscordProvider(NotificationProvider):
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def send(self, message: str) -> None:
        await _post(self._webhook_url, {"content": message})
