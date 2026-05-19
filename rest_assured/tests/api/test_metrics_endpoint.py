from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rest_assured.src.api.dependencies import get_metrics_service
from rest_assured.src.api.routers.metrics import router
from rest_assured.src.models.services import Service


class FakeMetricsService:
    def __init__(self, services: dict[int, Service]) -> None:
        self.services = services

    async def get_service(self, service_id: int) -> Service | None:
        return self.services.get(service_id)

    async def get_metrics(self, service_id: int) -> tuple[int, float]:
        if service_id == 3:
            return 0, 0.0
        return 42, 99.5


def make_app(services: dict[int, Service]) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_metrics_service] = lambda: FakeMetricsService(services)
    return app


@pytest.mark.asyncio
async def test_get_service_metrics_returns_200() -> None:
    app = make_app({1: Service(id=1, name="svc", url="http://example.com")})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/1/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["service_id"] == 1
    assert data["current_uptime_seconds"] == 42
    assert data["sla_pct"] == 99.5
    assert datetime.fromisoformat(data["computed_at"]) <= datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_get_service_metrics_returns_404_for_missing_service() -> None:
    app = make_app({})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/404/metrics")

    assert response.status_code == 404
    assert response.json()["detail"] == "service not found"


@pytest.mark.asyncio
async def test_get_service_metrics_service_without_checks_returns_zeroes() -> None:
    app = make_app({3: Service(id=3, name="empty", url="http://example.com")})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/3/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["current_uptime_seconds"] == 0
    assert data["sla_pct"] == 0.0


@pytest.mark.asyncio
async def test_get_service_metrics_without_authorization_header_returns_200() -> None:
    app = make_app({1: Service(id=1, name="svc", url="http://example.com")})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/1/metrics")

    assert response.status_code == 200
