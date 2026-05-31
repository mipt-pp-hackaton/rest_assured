"""Integration tests for T4 — the seed() routine.

``seed()`` provisions a superuser (``admin@admin.com`` / ``admin``) through the
service layer plus a fixed set of demo services (``DEMO_SERVICES``). The
routine must be idempotent: running it twice leaves exactly one admin row and
no duplicate service rows.

These tests need a real PostgreSQL (testcontainers) because they exercise the
DB-level unique constraints and the full service-layer write path.
``pytest.importorskip`` makes the module SKIP cleanly when Docker /
testcontainers are unavailable instead of raising a collection error.
"""

from __future__ import annotations

import pytest

pytest.importorskip("testcontainers")

from sqlmodel import select  # noqa: E402

from rest_assured.src.models.services import Service  # noqa: E402
from rest_assured.src.models.users import User  # noqa: E402
from rest_assured.src.scripts import seed as seed_module  # noqa: E402
from rest_assured.src.scripts.seed import seed  # noqa: E402
from rest_assured.src.services.auth.passwords import verify_password  # noqa: E402

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "admin"

# The demo service URLs are declared once, in production code — reference them
# rather than hardcoding so the tests track the real contract.
DEMO_URLS = [data.url for data in seed_module.DEMO_SERVICES]


async def test_seed_first_run_creates_admin(postgres_connection) -> None:
    """First invocation on a clean DB creates the admin superuser with the
    expected flags and a bcrypt hash that verifies against the seed password."""
    await seed()

    # seed() commits in its own session_scope() session, so expire the test
    # session's identity map to force a re-read from the DB.
    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(User).where(User.email == ADMIN_EMAIL))
    rows = result.all()

    assert len(rows) == 1, f"expected exactly 1 admin row, got {len(rows)}"
    admin = rows[0]
    assert admin.is_superuser is True
    assert admin.is_active is True
    assert verify_password(ADMIN_PASSWORD, admin.password_hash) is True


async def test_seed_first_run_creates_demo_services(postgres_connection) -> None:
    """First invocation creates the demo service rows; every URL declared in
    ``DEMO_SERVICES`` is present."""
    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(Service))
    services = list(result)

    assert len(services) >= 2, f"seed() should create at least 2 demo services, got {len(services)}"

    persisted_urls = {service.url for service in services}
    for url in DEMO_URLS:
        assert url in persisted_urls, f"demo URL {url!r} missing after seed(); got {persisted_urls}"


async def test_seed_is_idempotent(postgres_connection) -> None:
    """Running seed twice must not raise and must leave exactly one admin row."""
    await seed()
    # Second invocation must not raise — this is the contract under test.
    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(User).where(User.email == ADMIN_EMAIL))
    rows = result.all()
    assert len(rows) == 1, f"expected exactly 1 admin row after 2 seeds, got {len(rows)}"


async def test_seed_idempotent_does_not_duplicate_services(postgres_connection) -> None:
    """Running seed twice must not duplicate the demo services — each demo URL
    appears exactly once."""
    await seed()
    await seed()

    postgres_connection.expire_all()
    result = await postgres_connection.exec(select(Service))
    services = list(result)

    urls = [s.url for s in services]
    assert len(urls) == len(set(urls)), f"seed() created duplicate service rows: {urls}"
    for url in DEMO_URLS:
        assert urls.count(url) == 1, f"demo URL {url!r} appears {urls.count(url)} times, expected 1"
