from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from rest_assured.src.models.services import Service
from rest_assured.src.services import metrics_service as metrics_service_module
from rest_assured.src.services.metrics_service import MetricsService


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class FakeSession:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows
        self.exec_count = 0
        self.closed = False

    async def exec(self, statement: Any, **kwargs: Any) -> FakeResult:
        self.exec_count += 1
        return FakeResult(self.rows)

    async def close(self) -> None:
        self.closed = True


def make_check(base: datetime, seconds: int, is_up: bool) -> SimpleNamespace:
    return SimpleNamespace(checked_at=base + timedelta(seconds=seconds), is_up=is_up)


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    metrics_service_module.configure(cache_ttl_seconds=5)


@pytest.mark.asyncio
async def test_get_metrics_computes_uptime_and_sla() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = FakeSession(
        [
            make_check(base, 0, False),
            make_check(base, 10, True),
            make_check(base, 20, True),
            make_check(base, 30, True),
            make_check(base, 40, False),
            make_check(base, 50, True),
            make_check(base, 60, True),
        ]
    )
    service = MetricsService(session)

    uptime_seconds, sla_pct = await service.get_metrics(1)

    assert uptime_seconds == 10
    assert sla_pct == 50.0


@pytest.mark.asyncio
async def test_get_metrics_cache_hit_does_not_query_db_twice() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = FakeSession([make_check(base, 0, True), make_check(base, 10, True)])
    metrics_service_module.configure(cache_ttl_seconds=5)
    service = MetricsService(session)

    assert await service.get_metrics(1) == (10, 100.0)
    assert await service.get_metrics(1) == (10, 100.0)

    assert session.exec_count == 1


@pytest.mark.asyncio
async def test_get_metrics_cache_expire_invalidates_cache() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    metrics_service_module.configure(cache_ttl_seconds=5)
    session_first = FakeSession([make_check(base, 0, True), make_check(base, 10, True)])
    assert await MetricsService(session_first).get_metrics(1) == (10, 100.0)
    metrics_service_module._cache[1] = (10, 100.0, datetime(2020, 1, 1, tzinfo=timezone.utc))

    session_second = FakeSession(
        [
            make_check(base, 0, True),
            make_check(base, 10, False),
            make_check(base, 20, True),
        ]
    )
    assert await MetricsService(session_second).get_metrics(1) == (0, 0.0)


@pytest.mark.asyncio
async def test_get_summary_for_multiple_services() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    services = [
        Service(id=1, name="svc1", url="http://example.com/1", is_active=True),
        Service(id=2, name="svc2", url="http://example.com/2", is_active=True),
    ]

    class MultiSession:
        def __init__(self) -> None:
            self._queue: list[list[Any]] = [
                [(services[0], base + timedelta(seconds=20), True), (services[1], None, None)],
                [make_check(base, 0, True), make_check(base, 20, True)],
                [],
            ]
            self.exec_count = 0

        async def exec(self, statement: Any, **kwargs: Any) -> FakeResult:
            self.exec_count += 1
            return FakeResult(self._queue.pop(0))

        async def close(self) -> None:
            pass

    metrics_service_module.configure(cache_ttl_seconds=5)
    session = MultiSession()
    summary = await MetricsService(session).get_summary()

    assert [item.service_id for item in summary] == [1, 2]
    assert summary[0].current_uptime_seconds == 20
    assert summary[0].sla_pct == 100.0
    assert summary[0].last_check_at == base + timedelta(seconds=20)
    assert summary[0].last_check_is_up is True
    assert summary[1].current_uptime_seconds == 0
    assert summary[1].sla_pct == 0.0
    assert not session._queue
