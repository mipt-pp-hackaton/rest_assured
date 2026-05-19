import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import cast

from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.services import Service
from rest_assured.src.repositories.metrics import (
    fetch_active_services_with_last_check,
    fetch_checks_for_service,
    fetch_timeseries_buckets,
)
from rest_assured.src.schemas.metrics import ServiceSummaryItem, TimeseriesBucket
from rest_assured.src.services.metrics import (
    CheckResult as MetricsCheckResult,
)
from rest_assured.src.services.metrics import (
    compute_current_uptime,
    compute_sla,
)


class MetricsService:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        cache_ttl_seconds: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[int, tuple[int, float, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get_metrics(self, service_id: int) -> tuple[int, float]:
        cached = self._cache.get(service_id)
        if cached is not None and self._is_fresh(cached[2]):
            return cached[0], cached[1]

        async with self._lock:
            cached = self._cache.get(service_id)
            if cached is not None and self._is_fresh(cached[2]):
                return cached[0], cached[1]

            async with self._session_scope() as session:
                checks = cast(
                    list[MetricsCheckResult],
                    list(await fetch_checks_for_service(session, service_id)),
                )

            uptime_seconds = compute_current_uptime(checks)
            sla_pct = round(compute_sla(checks) * 100.0, 2)
            self._cache[service_id] = (uptime_seconds, sla_pct, self._now())
            return uptime_seconds, sla_pct

    async def get_service(self, service_id: int) -> Service | None:
        async with self._session_scope() as session:
            return await session.get(Service, service_id)

    async def get_summary(self) -> list[ServiceSummaryItem]:
        async with self._session_scope() as session:
            rows = await fetch_active_services_with_last_check(session)

        items: list[ServiceSummaryItem] = []
        for service, last_check_at, last_check_is_up in rows:
            if service.id is None:
                continue
            uptime_seconds, sla_pct = await self.get_metrics(service.id)
            items.append(
                ServiceSummaryItem(
                    service_id=service.id,
                    name=service.name,
                    url=service.url,
                    is_active=service.is_active,
                    current_uptime_seconds=uptime_seconds,
                    sla_pct=round(sla_pct, 2),
                    last_check_at=last_check_at,
                    last_check_is_up=last_check_is_up,
                )
            )
        return items

    async def get_timeseries(
        self,
        service_id: int,
        from_: datetime,
        to: datetime,
        bucket_seconds: int,
    ) -> list[TimeseriesBucket]:
        async with self._session_scope() as session:
            rows = await fetch_timeseries_buckets(session, service_id, from_, to, bucket_seconds)

        buckets: list[TimeseriesBucket] = []
        for row in rows:
            checks_total = int(row.checks_total)
            checks_up = int(row.checks_up)
            buckets.append(
                TimeseriesBucket(
                    bucket_start=row.bucket_start,
                    checks_total=checks_total,
                    checks_up=checks_up,
                    up_ratio=checks_up / checks_total,
                    latency_avg_ms=(
                        float(row.latency_avg_ms) if row.latency_avg_ms is not None else None
                    ),
                    latency_p95_ms=(
                        float(row.latency_p95_ms) if row.latency_p95_ms is not None else None
                    ),
                )
            )
        return buckets

    def _session_scope(self) -> "_SessionScope":
        return _SessionScope(self._session_factory())

    def _is_fresh(self, cached_at: datetime) -> bool:
        age = (self._now() - cached_at).total_seconds()
        return age < self._cache_ttl_seconds

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


class _SessionScope:
    """Async context manager that closes the session on exit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._session.close()
