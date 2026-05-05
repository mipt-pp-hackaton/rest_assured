import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class CheckResult(SQLModel, table=True):
    __tablename__ = "check_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    service_id: uuid.UUID = Field(foreign_key="services.id", index=True)
    is_up: bool
    response_time_ms: int | None = None
    status_code: int | None = None
    error_message: str | None = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)