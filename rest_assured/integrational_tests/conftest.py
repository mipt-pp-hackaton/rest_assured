import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Generator

import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from rest_assured.src.configs.app.main import settings
from rest_assured.src.main import app
from rest_assured.src.repositories.database_session import get_session


@pytest.fixture(autouse=True)
def _allow_test_hosts(monkeypatch):
    """Мокаем socket.getaddrinfo, чтобы тестовые URL (http://fake/...) проходили
    SSRF-валидацию модели Service (резолвим в публичный IP example.com)."""

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                0,
                "",
                ("93.184.216.34", port or 80),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


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
            host = postgres.get_container_host_ip()
            # Под WSL2/Linux testcontainers возвращает 'localhost', но asyncpg
            # резолвит его в IPv6 (::1), а контейнер слушает только IPv4 →
            # коннект уходит в TimeoutError. Принудительно ставим IPv4-loopback.
            if host in ("localhost", "::1"):
                host = "127.0.0.1"
            settings.db_settings.host = host

        run_migrations()
        yield
    finally:
        if postgres is not None:
            postgres.stop()


@pytest_asyncio.fixture
async def postgres_connection(_bootstrap_db) -> AsyncSession:
    import rest_assured.src.repositories.database_session as db_module

    # Перед тестом гарантируем чистый engine/sessionmaker, чтобы DSN из
    # testcontainer применился, и не было «протухших» коннектов с предыдущего теста.
    if db_module._engine is not None:
        try:
            await db_module._engine.dispose()
        except Exception:
            pass
    db_module._engine = None
    db_module._sessionmaker = None

    session = get_session()
    # Чистим таблицы перед каждым тестом, чтобы тесты были изолированы
    # (например, runner.start() читает все is_active=True сервисы, и сервисы
    # от предыдущих тестов поднимали бы фантомных воркеров).
    try:
        await session.execute(
            text("TRUNCATE TABLE check_results, services RESTART IDENTITY CASCADE")
        )
        await session.commit()
    except Exception:
        await session.rollback()
    try:
        yield session
    finally:
        # Перед закрытием — гасим любую активную транзакцию,
        # иначе AsyncSession.close() может упасть с IllegalStateChangeError
        # ('_connection_for_bind() is already in progress'), если предыдущий
        # тест/фоновый воркер оставил незавершённую транзакцию.
        try:
            await session.rollback()
        except Exception:
            pass
        try:
            await session.close()
        except Exception:
            pass
        # Диспозим engine, чтобы не оставлять открытых connection-ов между тестами.
        try:
            if db_module._engine is not None:
                await db_module._engine.dispose()
        except Exception:
            pass
        db_module._engine = None
        db_module._sessionmaker = None


def run_migrations(revision: str = "heads") -> None:
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    # Используем асинхронный DSN
    dsn = settings.db_settings.dsl

    result = subprocess.run(
        ["poetry", "run", "alembic", "-c", "alembic.ini", "upgrade", "heads"],
        capture_output=True, text=True, cwd=str(src_dir),
        env={**os.environ, "DB_DSN": dsn},
    )

    if result.returncode != 0:
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        raise RuntimeError("Миграции не накатились")


@pytest.fixture
def router_api():
    yield TestClient(app)


@pytest_asyncio.fixture
async def router_api_admin(postgres_connection):
    yield TestClient(app)
