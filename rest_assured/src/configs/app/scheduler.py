"""Настройки планировщика проверок."""

from pydantic import BaseModel


class SchedulerSettings(BaseModel):
    default_interval_ms: int = 60000
    http_timeout_seconds: float = 5.0
    max_retries: int = 2
    retry_delay_ms: int = 1000