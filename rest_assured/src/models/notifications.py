"""Модель лога уведомлений."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class NotificationLog(SQLModel, table=True):
    __tablename__ = "notification_log"
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int | None = Field(default=None, foreign_key="incidents.id", index=True)
    service_id: int = Field(foreign_key="services.id", index=True)
    kind: str = Field(max_length=50)
    sent_at: datetime
    recipients: str = Field(max_length=500)
    subject: str = Field(max_length=500)
    error: str | None = None
