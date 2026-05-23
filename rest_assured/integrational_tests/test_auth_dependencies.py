"""Integration tests for `get_current_active_user` / `get_current_superuser` (T7).

We mount a temporary router with two test-only endpoints that depend on the
two new authz predicates, then exercise them through a real ASGI client with
real JWTs against a real Postgres (via the conftest's testcontainers setup).

T9 will wire `get_current_superuser` into the actual catalog/admin routers;
until then this fixture-based mounting is the cleanest way to validate the
dependency-chain behavior end-to-end.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from rest_assured.src.main import app
from rest_assured.src.models.users import User
from rest_assured.src.services.auth.dependencies import (
    get_current_active_user,
    get_current_superuser,
)
from rest_assured.src.services.auth.jwt import create_access_token

_BASE_URL = "http://test"


@pytest_asyncio.fixture
async def app_with_test_router(postgres_connection) -> AsyncIterator[AsyncClient]:
    """Mount a throwaway router that exposes the T7 dependencies directly."""
    router = APIRouter()

    @router.get("/__test/active")
    async def _active_endpoint(user: User = Depends(get_current_active_user)) -> dict:
        return {"ok": True, "user_id": user.id}

    @router.get("/__test/superuser")
    async def _superuser_endpoint(user: User = Depends(get_current_superuser)) -> dict:
        return {"ok": True, "user_id": user.id}

    app.include_router(router)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            yield client
    finally:
        # Drop our test-only routes so we don't leak them across tests.
        app.router.routes = [
            r
            for r in app.router.routes
            if getattr(r, "path", None) not in {"/__test/active", "/__test/superuser"}
        ]


# ---------------------------------------------------------------------------
# /__test/active — guarded by get_current_active_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_active_endpoint_returns_200_for_active_user(
    app_with_test_router: AsyncClient, seed_user
) -> None:
    user = await seed_user("active@example.com", "secret123")
    token = create_access_token(user.id)

    resp = await app_with_test_router.get(
        "/__test/active", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "user_id": user.id}


@pytest.mark.asyncio
async def test_active_endpoint_returns_403_for_inactive_user(
    app_with_test_router: AsyncClient, seed_user, postgres_connection
) -> None:
    user = await seed_user("toggle@example.com", "secret123")
    token = create_access_token(user.id)

    # Flip is_active=False in DB *after* issuing the token.
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    resp = await app_with_test_router.get(
        "/__test/active", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Inactive user"}


# ---------------------------------------------------------------------------
# /__test/superuser — guarded by get_current_superuser
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_superuser_endpoint_rejects_regular_user_with_403(
    app_with_test_router: AsyncClient, seed_user
) -> None:
    user = await seed_user("regular@example.com", "secret123", is_superuser=False)
    token = create_access_token(user.id)

    resp = await app_with_test_router.get(
        "/__test/superuser", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Not enough privileges"}


@pytest.mark.asyncio
async def test_superuser_endpoint_returns_200_after_upgrade(
    app_with_test_router: AsyncClient, seed_user, postgres_connection
) -> None:
    user = await seed_user("promote@example.com", "secret123", is_superuser=False)
    token = create_access_token(user.id)

    # Initial call: not a superuser, expect 403.
    resp = await app_with_test_router.get(
        "/__test/superuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Not enough privileges"}

    # Promote to superuser in DB.
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_superuser=True))
    await postgres_connection.commit()

    # Re-call with the same token: now should succeed.
    resp = await app_with_test_router.get(
        "/__test/superuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "user_id": user.id}


@pytest.mark.asyncio
async def test_superuser_endpoint_inactive_superuser_sees_inactive_error_first(
    app_with_test_router: AsyncClient, seed_user, postgres_connection
) -> None:
    """An inactive superuser hitting a `get_current_superuser`-guarded endpoint
    must see 'Inactive user' (the active-user check fires first), not
    'Not enough privileges'."""
    user = await seed_user("inactive-root@example.com", "secret123", is_superuser=True)
    token = create_access_token(user.id)

    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    resp = await app_with_test_router.get(
        "/__test/superuser", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Inactive user"}
