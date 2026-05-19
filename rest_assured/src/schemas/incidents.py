from datetime import datetime

from pydantic import BaseModel


class IncidentRead(BaseModel):
    id: int
    service_id: int
    service_name: str
    opened_at: datetime
    closed_at: datetime | None
    last_error: str | None
    sla_breach: bool
    duration_seconds: int | None

    model_config = {"from_attributes": True}
