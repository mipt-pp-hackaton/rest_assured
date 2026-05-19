from collections import namedtuple
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rest_assured.src.api.routers.metrics import router
from rest_assured.src.models.services import Service

TimeseriesRow = namedtuple(
    "TimeseriesRow",
    ["bucket_start", "checks_total", "checks_up", "latency_avg_ms", "latency_p95_ms"],
)


class FakeResult:
    def __init__(self, rows: list[TimeseriesRow]) -> None:
        self._rows = rows

    def all(self) -> list[TimeseriesRow]:
        return self._rows


class FakeSession:
    def __init__(self, service: Service | None, checks: list[dict[str, Any]]) -> None:
        self.service = service
        self.checks = checks

    async def get(self, model: Any, item_id: int) -> Service | None:
        return self.service

    async def exec(self, statement: Any, params: dict[str, Any]) -> FakeResult:
        bucket = params["bucket"]
        from_ = params["from"]
        to = params["to"]
        grouped: dict[datetime, list[dict[str, Any]]] = {}
        for check in self.checks:
            checked_at = check["checked_at"]
            if checked_at < from_ or checked_at >= to:
                continue
            epoch = int(checked_at.timestamp())
            bucket_start = datetime.fromtimestamp((epoch // bucket) * bucket, tz=timezone.utc)
            grouped.setdefault(bucket_start, []).append(check)

        rows = []
        for bucket_start in sorted(grouped):
            bucket_checks = grouped[bucket_start]
            latencies = [check["latency_ms"] for check in bucket_checks]
            rows.append(
                TimeseriesRow(
                    bucket_start=bucket_start,
                    checks_total=len(bucket_checks),
                    checks_up=sum(1 for check in bucket_checks if check["is_up"]),
                    latency_avg_ms=sum(latencies) / len(latencies),
                    latency_p95_ms=percentile_cont(latencies, 0.95),
                )
            )
        return FakeResult(rows)

    async def close(self) -> None:
        pass


def percentile_cont(values: list[int], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * percentile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def make_app(service: Service | None, checks: list[dict[str, Any]]) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = lambda: FakeSession(service, checks)
    app.include_router(router)
    return app


def make_checks(count: int = 60) -> list[dict[str, Any]]:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return [
        {
            "checked_at": base + timedelta(seconds=i),
            "is_up": i % 3 != 0,
            "latency_ms": i % 10,
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_timeseries_sixty_checks_by_ten_seconds_returns_six_buckets() -> None:
    app = make_app(Service(id=1, name="svc", url="http://example.com"), make_checks())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/services/1/timeseries",
            params={
                "from": "2026-01-01T12:00:00Z",
                "to": "2026-01-01T12:01:00Z",
                "bucket_seconds": 10,
            },
        )

    assert response.status_code == 200
    assert len(response.json()) == 6


@pytest.mark.asyncio
async def test_timeseries_to_less_than_or_equal_from_returns_422() -> None:
    app = make_app(Service(id=1, name="svc", url="http://example.com"), [])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/services/1/timeseries",
            params={
                "from": "2026-01-01T12:00:00Z",
                "to": "2026-01-01T12:00:00Z",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_timeseries_missing_service_returns_404() -> None:
    app = make_app(None, [])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/services/404/timeseries",
            params={
                "from": "2026-01-01T12:00:00Z",
                "to": "2026-01-01T12:01:00Z",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "service not found"


@pytest.mark.asyncio
async def test_timeseries_empty_range_returns_empty_list() -> None:
    app = make_app(Service(id=1, name="svc", url="http://example.com"), make_checks())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/services/1/timeseries",
            params={
                "from": "2026-01-01T13:00:00Z",
                "to": "2026-01-01T14:00:00Z",
            },
        )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_timeseries_returns_p95_latency() -> None:
    app = make_app(Service(id=1, name="svc", url="http://example.com"), make_checks(10))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/services/1/timeseries",
            params={
                "from": "2026-01-01T12:00:00Z",
                "to": "2026-01-01T12:00:10Z",
                "bucket_seconds": 10,
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["latency_p95_ms"] == pytest.approx(8.55)
