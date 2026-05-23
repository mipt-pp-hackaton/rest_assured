"""Seed-скрипт: создаёт админа и демо-сервисы."""

import asyncio
import os

from sqlmodel import select

from rest_assured.src.models.services import Service
from rest_assured.src.models.users import User
from rest_assured.src.repositories.database_session import session_scope
from rest_assured.src.services.auth.passwords import hash_password


def build_admin_user() -> User:
    password = os.environ.get("SEED_ADMIN_PASSWORD", "")
    if not password.strip():
        raise RuntimeError("SEED_ADMIN_PASSWORD env var is required")
    return User(
        email="admin@example.com",
        password_hash=hash_password(password),
        is_superuser=True,
    )


def _demo_services() -> list[Service]:
    return [
        Service(
            url="https://httpbin.org/get",
            name="Demo HTTP Bin",
            http_method="GET",
            interval_ms=30000,
            is_active=True,
        ),
        Service(
            url="https://example.com",
            name="Example Com",
            http_method="GET",
            interval_ms=60000,
            is_active=True,
        ),
    ]


async def seed() -> None:
    admin = build_admin_user()
    async with session_scope() as session:
        # Admin user — skip if email already exists (idempotent).
        existing_admin = await session.exec(select(User).where(User.email == admin.email))
        if existing_admin.first() is None:
            session.add(admin)

        # Demo services — skip if url already exists (no DB-level unique
        # constraint on services.url, so the dedup is done in app code).
        for service in _demo_services():
            existing = await session.exec(select(Service).where(Service.url == service.url))
            if existing.first() is None:
                session.add(service)

        await session.commit()
    print("Seed completed: admin@example.com + 2 demo services")


if __name__ == "__main__":
    asyncio.run(seed())
