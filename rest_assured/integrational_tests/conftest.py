import os
import subprocess
from pathlib import Path
from typing import Any, Generator

import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from rest_assured.src.configs.app.main import settings
from rest_assured.src.main import app
from rest_assured.src.repositories.database_session import get_session


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
            settings.db_settings.password = postgres.password
            settings.db_settings.host = postgres.get_container_host_ip()

        run_migrations()
        yield
    finally:
        if postgres is not None:
            postgres.stop()


@pytest_asyncio.fixture
async def postgres_connection(_bootstrap_db) -> AsyncSession:
    import rest_assured.src.repositories.database_session as db_module
    db_module._engine = None
    db_module._sessionmaker = None

    session = get_session()
    try:
        yield session
    finally:
        await session.close()


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
