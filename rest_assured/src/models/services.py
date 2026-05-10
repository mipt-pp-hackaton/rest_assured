"""Модель отслеживаемого сервиса."""

import ipaddress
import socket
from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import field_validator
from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


def validate_public_url(url: str) -> str:
    """Проверяет, что URL имеет http/https-схему и резолвится в публичный IP.

    Защита от SSRF: запрещаются loopback, RFC-1918 private, link-local
    (включая 169.254.169.254 cloud-metadata), multicast, reserved, unspecified.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"url scheme must be http or https, got: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError("url has no hostname")
    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
        )
    except socket.gaierror as e:
        raise ValueError(f"url hostname not resolvable: {parsed.hostname}") from e
    for _, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError(f"url resolves to non-public IP: {ip}")
    return url


class Service(SQLModel, table=True):
    """Сервис, за которым ведётся наблюдение."""

    __tablename__ = "services"
    model_config = {"validate_assignment": True}

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(max_length=2048, description="URL сервиса для мониторинга")
    name: str = Field(max_length=255, description="Название сервиса")
    http_method: Literal[
        "GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"
    ] = Field(
        default="GET",
        description="HTTP метод для проверки (GET, POST, HEAD и т.д.)",
        sa_column=Column(String(16), nullable=False, default="GET"),
    )
    interval_ms: int = Field(
        default=60000,
        ge=1000,
        description="Интервал проверки в миллисекундах (минимум 1000)",
    )
    expected_status: Optional[int] = Field(
        default=None,
        description="Ожидаемый HTTP статус (если None, то 200-299 считается успехом)",
    )
    is_active: bool = Field(default=True, description="Активен ли сервис")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Дата создания",
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        return validate_public_url(v)
