"""Модель инцидента."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class Incident(SQLModel, table=True):
    """Инцидент недоступности сервиса."""

    __tablename__ = "incidents"

    id: int | None = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.id", index=True)
    opened_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    closed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    last_error: str | None = Field(default=None, max_length=500)
    sla_breach: bool = Field(default=False)
