"""Модель лога уведомлений."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class NotificationLog(SQLModel, table=True):
    """Запись об отправленном уведомлении."""

    __tablename__ = "notification_log"

    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(
        default=None,
        foreign_key="incidents.id",
        index=True,
    )
    service_id: int = Field(foreign_key="services.id", index=True)
    kind: str = Field(max_length=50)
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    recipients: str = Field(max_length=500)
    subject: str = Field(max_length=500)
    error: str | None = Field(default=None, max_length=500)
