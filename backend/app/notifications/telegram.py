from app.notifications.base import NotificationProvider, _post


class TelegramProvider(NotificationProvider):
    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def send(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        await _post(url, {"chat_id": self._chat_id, "text": message})
