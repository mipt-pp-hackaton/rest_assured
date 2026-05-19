"""Seed-скрипт: создаёт админа и демо-сервисы."""

import asyncio

from rest_assured.src.auth.passwords import hash_password
from rest_assured.src.models.services import Service
from rest_assured.src.models.user import User
from rest_assured.src.repositories.database_session import get_session


async def seed() -> None:
    session = get_session()
    try:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("admin"),
            is_admin=True,
        )
        session.add(admin)

        svc1 = Service(
            url="https://httpbin.org/get",
            name="Demo HTTP Bin",
            http_method="GET",
            interval_ms=30000,
            is_active=True,
        )
        svc2 = Service(
            url="https://example.com",
            name="Example Com",
            http_method="GET",
            interval_ms=60000,
            is_active=True,
        )
        session.add(svc1)
        session.add(svc2)

        await session.commit()
        print("Seed completed: admin@example.com / admin + 2 demo services")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(seed())
