from datetime import time

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    scheduler_time: time
    timezone: str
    default_grace_period_hours: int
    executor_interval_minutes: int
    log_retention_days: int


class AppSettingsUpdateRequest(BaseModel):
    scheduler_time: time
    timezone: str
    default_grace_period_hours: int
    executor_interval_minutes: int
    log_retention_days: int
