from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rest_assured.src.api.routers.metrics import router
from rest_assured.src.schemas.metrics import ServiceSummaryItem


class FakeMetricsService:
    def __init__(self, rows: list[ServiceSummaryItem]) -> None:
        self.rows = rows

    async def get_summary(self) -> list[ServiceSummaryItem]:
        return self.rows


def make_app(rows: list[ServiceSummaryItem]) -> FastAPI:
    app = FastAPI()
    app.state.metrics_service = FakeMetricsService(rows)
    app.include_router(router)
    return app


def item(
    service_id: int,
    *,
    is_active: bool = True,
    last_check_at: datetime | None = None,
    last_check_is_up: bool | None = None,
) -> ServiceSummaryItem:
    return ServiceSummaryItem(
        service_id=service_id,
        name=f"svc{service_id}",
        url=f"http://example.com/{service_id}",
        is_active=is_active,
        current_uptime_seconds=service_id * 10,
        sla_pct=90.0 + service_id,
        last_check_at=last_check_at,
        last_check_is_up=last_check_is_up,
    )


@pytest.mark.asyncio
async def test_summary_empty_services_returns_empty_list() -> None:
    app = make_app([])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/summary")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_summary_returns_three_services_in_order() -> None:
    app = make_app([item(1), item(2), item(3)])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/summary")

    assert response.status_code == 200
    assert [row["service_id"] for row in response.json()] == [1, 2, 3]


@pytest.mark.asyncio
async def test_summary_does_not_include_inactive_service() -> None:
    app = make_app([item(1), item(3)])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/summary")

    assert response.status_code == 200
    assert [row["service_id"] for row in response.json()] == [1, 3]


@pytest.mark.asyncio
async def test_summary_returns_last_check_fields() -> None:
    last_check_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    app = make_app([item(1, last_check_at=last_check_at, last_check_is_up=True)])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/summary")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["last_check_at"] == "2026-01-01T12:00:00Z"
    assert data[0]["last_check_is_up"] is True
