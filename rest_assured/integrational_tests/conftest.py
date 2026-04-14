import os
from typing import Generator, Any

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
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
        if settings.app.use_testcontainers:
            postgres = PostgresContainer("postgres:18-alpine")
            postgres.start()
            settings.db.name = postgres.dbname
            settings.db.port = int(postgres.get_exposed_port(5432))
            settings.db.user = postgres.username
            settings.db.password = postgres.password
            settings.db.host = postgres.get_container_host_ip()

        run_migrations()
        yield
    finally:
        if postgres is not None:
            postgres.stop()


@pytest_asyncio.fixture
async def postgres_connection(_bootstrap_db) -> AsyncSession:
    agen = get_session()
    session = await agen.__anext__()
    try:
        yield session
    finally:
        await agen.aclose()


def run_migrations(revision: str = "heads") -> None:
    repo_root = os.path.dirname(os.path.dirname(__file__))  # .../rest_assured
    alembic_ini_path = os.path.join(repo_root, "src", "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(config=alembic_cfg, revision=revision)


@pytest.fixture
def router_api():
    client = TestClient(app)
    yield client


@pytest_asyncio.fixture
async def router_api_admin(postgres_connection):
    client = TestClient(app)
    yield client