"""Seed-данные: админ + демо-сервисы через сервисный слой.

Идемпотентно — повторный запуск ничего не дублирует. Запускается из CLI:
``python3 -m rest_assured --seed``.
"""

import asyncio
import logging

from rest_assured.src.repositories.database_session import session_scope
from rest_assured.src.schemas.services import ServiceCreate
from rest_assured.src.services.auth.service import AuthService
from rest_assured.src.services.catalog import CatalogService

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin"

DEMO_SERVICES: list[ServiceCreate] = [
    ServiceCreate(
        url="https://httpbin.org/get",
        name="Demo HTTP Bin",
        http_method="GET",
        interval_ms=30000,
    ),
    ServiceCreate(
        url="https://example.com",
        name="Example Com",
        http_method="GET",
        interval_ms=60000,
    ),
]


async def seed() -> None:
    """Создаёт админа и демо-сервисы через AuthService / CatalogService."""
    async with session_scope() as session:
        auth = AuthService(session)
        catalog = CatalogService(session)

        await auth.ensure_superuser(ADMIN_EMAIL, ADMIN_PASSWORD)

        existing_urls = {service.url for service in await catalog.list_all()}
        created = 0
        for data in DEMO_SERVICES:
            if data.url in existing_urls:
                continue
            await catalog.create(data)
            created += 1

    logger.info(
        "Seed completed: admin=%s, demo services created=%d (skipped=%d)",
        ADMIN_EMAIL,
        created,
        len(DEMO_SERVICES) - created,
    )


if __name__ == "__main__":
    asyncio.run(seed())
