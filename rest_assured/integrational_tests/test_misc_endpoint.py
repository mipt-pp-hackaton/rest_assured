"""GET /health и GET /api/health/scheduler."""

import pytest
from sqlalchemy import update

from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import create_access_token, create_refresh_token


@pytest.mark.asyncio
async def test_health_returns_ok(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_is_public_no_token_required(async_client):
    """T13 contract: liveness probe /health MUST stay open — no Authorization needed.

    Sanity-check that protecting /api/health/scheduler did NOT accidentally
    cover /health (it lives on a different router with no auth dep).
    """
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scheduler_health_returns_runner_stats(override_auth, router_api):
    """router_api поднимает lifespan, благодаря чему app.state.runner инициализирован."""
    response = router_api.get("/api/health/scheduler")
    assert response.status_code == 200
    stats = response.json()
    # Контракт: всегда возвращаются три счётчика
    assert set(stats.keys()) == {"checks_total", "checks_failed", "active_workers_count"}
    assert all(isinstance(v, int) and v >= 0 for v in stats.values())


# ---------------------------------------------------------------------------
# T13 — router-level auth on /api/health/scheduler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_health_requires_auth(async_client):
    """T13 RED: GET /api/health/scheduler без токена → 401."""
    response = await async_client.get("/api/health/scheduler")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scheduler_health_with_active_token_returns_200(router_api, seed_user):
    """T13 GREEN-side: активный юзер + валидный access token → 200.

    Используем router_api (sync TestClient) чтобы lifespan поднял app.state.runner.
    """
    user = await seed_user("scheduler-active@example.com", "secret123")
    token = create_access_token(user.id)
    response = router_api.get("/api/health/scheduler", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    stats = response.json()
    assert set(stats.keys()) == {"checks_total", "checks_failed", "active_workers_count"}


@pytest.mark.asyncio
async def test_scheduler_health_inactive_user_returns_403(
    async_client, seed_user, postgres_connection
):
    """T13 RED: is_active=False → 403 'Inactive user'."""
    user = await seed_user("inactive-scheduler@example.com", "secret123")
    token = create_access_token(user.id)
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.get(
        "/api/health/scheduler", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_scheduler_health_refresh_token_rejected(async_client, seed_user):
    """T13 RED: refresh token вместо access → 401 'Invalid token type'."""
    user = await seed_user("refresh-scheduler@example.com", "secret123")
    refresh = create_refresh_token(user.id)
    response = await async_client.get(
        "/api/health/scheduler", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token type"}
