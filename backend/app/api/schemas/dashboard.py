from pydantic import BaseModel


class WatchedStatusItem(BaseModel):
    title: str
    media_type: str
    jellyfin_item_id: str | None
    watched_at: str | None
    rule_id: int
    rule_name: str
    status: str
    threshold_value: int
    threshold_unit: str
    hours_remaining: float | None


class WatchedStatusResponse(BaseModel):
    approaching: list[WatchedStatusItem]
    exempt: list[WatchedStatusItem]
