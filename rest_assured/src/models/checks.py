"""Модель результата проверки сервиса (T2.3)."""

from datetime import datetime, timezone

from sqlalchemy import Index, desc
from sqlmodel import Field, SQLModel


class CheckResult(SQLModel, table=True):
    """Результат одной проверки доступности сервиса."""

    __tablename__ = "check_results"
    __table_args__ = (
        Index(
            "ix_check_results_service_checked_desc",
            "service_id",
            desc("checked_at"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.id", index=True)
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    is_up: bool = Field(description="Статус доступности сервиса")
    http_status: int | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    error: str | None = Field(default=None, max_length=500)
