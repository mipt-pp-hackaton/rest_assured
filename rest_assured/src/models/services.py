"""Модель отслеживаемого сервиса."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Service(SQLModel, table=True):
    """Сервис, за которым ведётся наблюдение."""

    __tablename__ = "services"

    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(description="URL сервиса для мониторинга")
    name: str = Field(description="Название сервиса")
    http_method: str = Field(
        default="GET",
        description="HTTP метод для проверки (GET, POST, HEAD и т.д.)",
    )
    interval_ms: int = Field(
        default=60000,
        description="Интервал проверки в миллисекундах",
    )
    expected_status: Optional[int] = Field(
        default=None,
        description="Ожидаемый HTTP статус (если None, то 200-299 считается успехом)",
    )
    is_active: bool = Field(default=True, description="Активен ли сервис")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Дата создания",
    )
