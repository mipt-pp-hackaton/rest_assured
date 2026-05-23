"""Integration tests for Improvement B — seed() must be idempotent.

Running ``python -m rest_assured.src.scripts.seed`` a second time currently
crashes with IntegrityError on the unique constraint of ``users.email`` (and
likely on demo service URL/name as well). After the fix, the second
invocation must succeed without raising and must NOT create duplicate rows.

These tests need a real PostgreSQL (testcontainers) because we are exercising
DB-level unique constraints; ``pytest.importorskip`` ensures we skip
explicitly when Docker / testcontainers are unavailable rather than failing
in a confusing way.
"""

from __future__ import annotations

import pytest

pytest.importorskip("testcontainers")

from sqlmodel import select  # noqa: E402

from rest_assured.src.models.services import Service  # noqa: E402
from rest_assured.src.models.users import User  # noqa: E402


async def test_seed_first_run_creates_admin(
    monkeypatch: pytest.MonkeyPatch, postgres_connection
) -> None:
    """First invocation on a clean DB must create the admin user with the
    expected flags."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "test-password-12345678")

    from rest_assured.src.scripts.seed import seed

    await seed()

    # Force the test session to re-read from the DB — seed() commits via
    # its own session, so without this we might be looking at stale state.
    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(User).where(User.email == "admin@example.com"))
    admin = result.first()
    assert admin is not None, "seed() did not create the admin user"
    assert admin.is_superuser is True
    assert admin.is_active is True


async def test_seed_first_run_creates_demo_services(
    monkeypatch: pytest.MonkeyPatch, postgres_connection
) -> None:
    """First invocation must create the demo services rows."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "test-password-12345678")

    from rest_assured.src.scripts.seed import seed

    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(Service))
    services = list(result)
    assert len(services) >= 2, f"seed() should create at least 2 demo services, got {len(services)}"


async def test_seed_is_idempotent(monkeypatch: pytest.MonkeyPatch, postgres_connection) -> None:
    """Running seed twice must not crash and must leave exactly one admin row."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "test-password-12345678")

    from rest_assured.src.scripts.seed import seed

    await seed()
    # Second invocation must not raise — this is the contract under test.
    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(User).where(User.email == "admin@example.com"))
    rows = list(result)
    assert len(rows) == 1, f"expected exactly 1 admin row after 2 seeds, got {len(rows)}"


async def test_seed_idempotent_does_not_duplicate_services(
    monkeypatch: pytest.MonkeyPatch, postgres_connection
) -> None:
    """Running seed twice must not duplicate the demo services."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "test-password-12345678")

    from rest_assured.src.scripts.seed import seed

    await seed()
    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(Service))
    services = list(result)
    # Group by URL — after two seeds, each demo URL should still appear once.
    urls = [s.url for s in services]
    assert len(urls) == len(set(urls)), f"seed() created duplicate service rows: {urls}"
