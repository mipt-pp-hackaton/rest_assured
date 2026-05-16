"""Модель инцидента."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Incident(SQLModel, table=True):
    __tablename__ = "incidents"
    id: int | None = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.id", index=True)
    opened_at: datetime
    closed_at: datetime | None = Field(default=None, index=True)
    last_error: str | None = None
    sla_breach: bool = Field(default=False)
