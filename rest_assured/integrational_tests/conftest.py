import os
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Generator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from rest_assured.src.configs.app.main import settings
from rest_assured.src.main import app
from rest_assured.src.models.services import Service
from rest_assured.src.models.users import User
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.services.auth.jwt import create_access_token
from rest_assured.src.services.auth.passwords import hash_password
from rest_assured.src.services.metrics_service import configure as configure_metrics_cache

_BASE_URL = "http://test"


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_db() -> Generator[None, Any, None]:
    postgres = None
    try:
        if settings.app_settings.use_testcontainers:
            postgres = PostgresContainer("postgres:18-alpine")
            postgres.start()
            settings.db_settings.name = postgres.dbname
            settings.db_settings.port = int(postgres.get_exposed_port(5432))
            settings.db_settings.user = postgres.username
            settings.db_settings.password = SecretStr(postgres.password)
            settings.db_settings.host = postgres.get_container_host_ip()
        run_migrations()
        # ASGITransport не запускает lifespan, поэтому отключаем кэш метрик вручную
        configure_metrics_cache(cache_ttl_seconds=0)
        yield
    finally:
        if postgres is not None:
            postgres.stop()


@pytest_asyncio.fixture
async def postgres_connection(_bootstrap_db) -> AsyncIterator[AsyncSession]:
    session = get_session()
    from sqlalchemy import text

    await session.exec(
        text(
            "TRUNCATE TABLE check_results, services, incidents, "
            "notification_log, users RESTART IDENTITY CASCADE"
        )
    )
    await session.commit()
    # Сбрасываем кэш метрик между тестами, чтобы сериальные id=1 не получали
    # закэшированные нули от предыдущего теста.
    configure_metrics_cache(cache_ttl_seconds=0)
    try:
        yield session
    finally:
        await session.close()


def run_migrations(revision: str = "heads") -> None:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    alembic_ini_path = os.path.join(repo_root, "src", "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(config=alembic_cfg, revision=revision)


# ---------------------------------------------------------------------------
# HTTP clients
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_client(postgres_connection) -> AsyncIterator[AsyncClient]:
    """Async HTTP-клиент поверх ASGITransport с чистой БД на каждый тест."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        yield client


@pytest.fixture
def router_api() -> Generator[TestClient, Any, None]:
    """Sync TestClient — запускает lifespan приложения (нужен для проверки startup-хуков)."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def override_auth() -> Generator[None, Any, None]:
    """Подменяет get_current_user на фиктивного админа — для тестов авторизованных
    эндпоинтов без поднятия пары login + JWT.

    Возвращаем активного суперюзера, чтобы override прошёл и через
    get_current_active_user, и через get_current_superuser-цепочки.
    """
    from rest_assured.src.services.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="admin@example.com",
        password_hash="",
        is_active=True,
        is_superuser=True,
    )
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Data-seeding factories
# ---------------------------------------------------------------------------


SeedServiceFn = Callable[..., Awaitable[Service]]
SeedUserFn = Callable[..., Awaitable[User]]


@pytest_asyncio.fixture
async def seed_service(postgres_connection: AsyncSession) -> SeedServiceFn:
    """Factory-фикстура: создаёт Service в БД и возвращает обновлённый объект.

    >>> svc = await seed_service(name="svc-a", interval_ms=5000)
    """
    defaults: dict[str, Any] = {
        "name": "Test Service",
        "url": "http://example.com",
        "interval_ms": 60000,
    }

    async def _seed(**overrides: Any) -> Service:
        data = {**defaults, **overrides}
        service = Service(**data)
        postgres_connection.add(service)
        await postgres_connection.commit()
        await postgres_connection.refresh(service)
        return service

    return _seed


@pytest_asyncio.fixture
async def seed_user(postgres_connection: AsyncSession) -> SeedUserFn:
    """Factory: создаёт пользователя с захэшированным паролем."""

    async def _seed(
        email: str = "user@example.com",
        password: str = "secret123",
        is_superuser: bool = False,
    ) -> User:
        user = User(email=email, password_hash=hash_password(password), is_superuser=is_superuser)
        postgres_connection.add(user)
        await postgres_connection.commit()
        await postgres_connection.refresh(user)
        return user

    return _seed


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def auth_token(seed_user: SeedUserFn) -> str:
    """Сидит дефолтного юзера и возвращает свежий JWT."""
    user = await seed_user("auth@example.com", "secret123")
    return create_access_token(user.id)


@pytest_asyncio.fixture
async def authorized_client(
    async_client: AsyncClient, auth_token: str
) -> AsyncIterator[AsyncClient]:
    """Async-клиент с уже выставленным Authorization-заголовком."""
    async_client.headers["Authorization"] = f"Bearer {auth_token}"
    yield async_client
