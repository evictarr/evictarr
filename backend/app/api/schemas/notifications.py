from pydantic import BaseModel

from app.db.models import NotificationProviderName


class NotificationConfigOut(BaseModel):
    provider: NotificationProviderName
    enabled: bool
    config_summary: dict
    notify_on_stage: bool
    notify_on_execute: bool
    notify_daily_summary: bool


class NotificationConfigUpdateRequest(BaseModel):
    enabled: bool
    # Discord: {"webhook_url": "..."}. Telegram: {"bot_token": "...", "chat_id": "..."}.
    # Omit a secret field (or send it blank) to keep the currently stored value.
    config: dict = {}
    notify_on_stage: bool = True
    notify_on_execute: bool = True
    notify_daily_summary: bool = True


class NotificationTestResponse(BaseModel):
    ok: bool
    detail: str
