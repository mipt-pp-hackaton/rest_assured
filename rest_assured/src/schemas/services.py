from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from rest_assured.src.models.services import validate_public_url


class ServiceCreate(BaseModel):
    url: str = Field(max_length=2048)
    name: str = Field(max_length=255)
    http_method: Literal["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"] = "GET"
    interval_ms: int = Field(default=60000, ge=1000)
    expected_status: Optional[int] = None
    is_active: bool = True

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        return validate_public_url(v)


class ServiceUpdate(BaseModel):
    url: Optional[str] = Field(default=None, max_length=2048)
    name: Optional[str] = Field(default=None, max_length=255)
    http_method: Optional[Literal["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"]] = (
        None
    )
    interval_ms: Optional[int] = Field(default=None, ge=1000)
    expected_status: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_public_url(v) if v is not None else v


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
