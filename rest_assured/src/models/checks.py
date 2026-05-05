"""Модель результата проверки сервиса."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class CheckResult(SQLModel, table=True):
    """Результат одной проверки доступности сервиса."""
    __tablename__ = "check_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    service_id: UUID = Field(foreign_key="services.id", index=True)
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    is_up: bool = Field(description="Статус доступности сервиса")
    response_time_ms: float | None = Field(default=None)
    status_code: int | None = Field(default=None)
    error_message: str | None = Field(default=None)

    model_config = {
        "indexes": [("service_id", "checked_at desc")],
    }
