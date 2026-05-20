"""GET /health и GET /api/health/scheduler."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scheduler_health_returns_runner_stats(router_api):
    """router_api поднимает lifespan, благодаря чему app.state.runner инициализирован."""
    response = router_api.get("/api/health/scheduler")
    assert response.status_code == 200
    stats = response.json()
    # Контракт: всегда возвращаются три счётчика
    assert set(stats.keys()) == {"checks_total", "checks_failed", "active_workers_count"}
    assert all(isinstance(v, int) and v >= 0 for v in stats.values())
