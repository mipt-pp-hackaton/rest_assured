from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ServiceCreate(BaseModel):
    url: str
    name: str
    http_method: Literal["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"] = "GET"
    interval_ms: int = 60000
    expected_status: Optional[int] = None
    is_active: bool = True


class ServiceUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    http_method: Optional[Literal["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"]] = (
        None
    )
    interval_ms: Optional[int] = None
    expected_status: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceRead(BaseModel):
    id: int
    url: str
    name: str
    http_method: str
    interval_ms: int
    expected_status: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
