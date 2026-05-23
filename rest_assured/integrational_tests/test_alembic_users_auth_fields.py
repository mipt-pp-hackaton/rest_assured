"""Integration tests for the Alembic revision that adds is_active,
is_superuser, updated_at to ``users`` and drops the legacy ``is_admin``.

These tests use a DEDICATED Postgres testcontainer (separate from the
shared one in conftest.py) so they can run ``alembic upgrade head``
followed by ``alembic downgrade -1`` without disturbing the shared DB.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from typing import Set

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

# Skip the whole module if Docker / testcontainers is unavailable.
docker = pytest.importorskip("docker")
testcontainers_postgres = pytest.importorskip("testcontainers.postgres")
PostgresContainer = testcontainers_postgres.PostgresContainer  # type: ignore[attr-defined]


REPO_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
ALEMBIC_INI = os.path.join(REPO_SRC, "alembic.ini")


def _check_docker_or_skip() -> None:
    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"docker not available: {exc}")


def _users_columns(async_dsn: str) -> Set[str]:
    """Read the column names of the ``users`` table from the running DB."""

    async def _inner() -> Set[str]:
        engine = create_async_engine(async_dsn)
        try:
            async with engine.connect() as conn:
                cols = await conn.run_sync(
                    lambda sync_conn: {
                        c["name"] for c in sa_inspect(sync_conn).get_columns("users")
                    }
                )
            return cols
        finally:
            await engine.dispose()

    return asyncio.run(_inner())


@pytest.fixture(scope="module")
def isolated_postgres() -> Iterator[str]:
    """Spin up a dedicated Postgres container for migration up/down tests.

    Yields the async DSN string.
    """
    _check_docker_or_skip()
    container = PostgresContainer("postgres:18-alpine")
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        user = container.username
        password = container.password
        dbname = container.dbname
        async_dsn = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
        # Patch settings so env.py picks up this container even via the
        # settings.db_settings fallback path.
        from rest_assured.src.configs.app.main import settings

        original = (
            settings.db_settings.host,
            settings.db_settings.port,
            settings.db_settings.user,
            settings.db_settings.password,
            settings.db_settings.name,
        )
        settings.db_settings.host = host
        settings.db_settings.port = port
        settings.db_settings.user = user
        settings.db_settings.password = SecretStr(password)
        settings.db_settings.name = dbname
        os.environ["DB_DSN"] = async_dsn
        try:
            yield async_dsn
        finally:
            (
                settings.db_settings.host,
                settings.db_settings.port,
                settings.db_settings.user,
                settings.db_settings.password,
                settings.db_settings.name,
            ) = original
            os.environ.pop("DB_DSN", None)
    finally:
        container.stop()


def _alembic_config() -> Config:
    return Config(ALEMBIC_INI)


def test_alembic_upgrade_head_adds_user_auth_fields(
    isolated_postgres: str,
) -> None:
    """Acceptance criterion #3: after ``alembic upgrade head`` the users
    table has is_active, is_superuser, updated_at AND NOT is_admin."""
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    cols = _users_columns(isolated_postgres)

    missing = {"is_active", "is_superuser", "updated_at"} - cols
    assert not missing, (
        f"users table missing columns after upgrade head: {missing}; " f"present: {sorted(cols)}"
    )
    assert "is_admin" not in cols, (
        f"users.is_admin should have been dropped by the new migration; "
        f"present columns: {sorted(cols)}"
    )


def test_alembic_downgrade_reverses_user_auth_fields(
    isolated_postgres: str,
) -> None:
    """Acceptance criterion #4: ``alembic downgrade -1`` (after upgrade)
    removes the three new columns and restores is_admin."""
    cfg = _alembic_config()
    # Make sure we're at head first.
    command.upgrade(cfg, "head")
    # Step back one revision.
    command.downgrade(cfg, "-1")

    cols = _users_columns(isolated_postgres)

    still_present = {"is_active", "is_superuser", "updated_at"} & cols
    assert not still_present, (
        f"downgrade should have removed {still_present} from users; " f"present: {sorted(cols)}"
    )
    assert (
        "is_admin" in cols
    ), f"downgrade should have restored users.is_admin; present: {sorted(cols)}"

    # Leave the DB at head so subsequent tests in this module (if any) are happy.
    command.upgrade(cfg, "head")


def test_alembic_upgrade_then_downgrade_then_upgrade_is_idempotent(
    isolated_postgres: str,
) -> None:
    """Sanity: up-down-up must converge to the same schema (no leftover
    constraints, no duplicate columns)."""
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")

    cols = _users_columns(isolated_postgres)
    for name in ("is_active", "is_superuser", "updated_at"):
        assert name in cols, f"expected column {name!r} after up-down-up cycle"
    assert "is_admin" not in cols, (
        "is_admin should not reappear after final upgrade; " f"present columns: {sorted(cols)}"
    )
