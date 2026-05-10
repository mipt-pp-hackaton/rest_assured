"""Настройки планировщика проверок."""

from pydantic import BaseModel


class SchedulerSettings(BaseModel):
    """Конфигурация планировщика в соответствии с T2.1."""

    poll_interval_seconds: int = 5
    default_timeout_ms: int = 5000
