import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class Service(SQLModel, table=True):
    __tablename__ = "services"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    url: str
    name: str
    interval_ms: int = 60000
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
