from datetime import datetime, timezone
from typing import cast

from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.services import Service
from rest_assured.src.repositories.metrics import (
    fetch_active_services_with_last_check,
    fetch_checks_for_service,
    fetch_timeseries_buckets,
)
from rest_assured.src.schemas.checks import CheckResultProtocol
from rest_assured.src.schemas.metrics import ServiceSummaryItem, TimeseriesBucket
from rest_assured.src.services.metrics import compute_current_uptime, compute_sla

_cache: dict[int, tuple[int, float, datetime]] = {}
_cache_ttl_seconds: int = 5


def configure(*, cache_ttl_seconds: int) -> None:
    """Reconfigure module-level metrics cache.

    Called from app startup and from tests that need to disable caching.
    """
    global _cache_ttl_seconds
    _cache_ttl_seconds = cache_ttl_seconds
    _cache.clear()


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_metrics(self, service_id: int) -> tuple[int, float]:
        cached = _cache.get(service_id)
        if cached is not None and self._is_fresh(cached[2]):
            return cached[0], cached[1]

        checks = cast(
            list[CheckResultProtocol],
            list(await fetch_checks_for_service(self._session, service_id)),
        )
        uptime_seconds = compute_current_uptime(checks)
        sla_pct = round(compute_sla(checks) * 100.0, 2)
        _cache[service_id] = (uptime_seconds, sla_pct, self._now())
        return uptime_seconds, sla_pct

    async def get_service(self, service_id: int) -> Service | None:
        return await self._session.get(Service, service_id)

    async def get_summary(self) -> list[ServiceSummaryItem]:
        rows = await fetch_active_services_with_last_check(self._session)

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
        rows = await fetch_timeseries_buckets(
            self._session, service_id, from_, to, bucket_seconds
        )

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

    @staticmethod
    def _is_fresh(cached_at: datetime) -> bool:
        age = (MetricsService._now() - cached_at).total_seconds()
        return age < _cache_ttl_seconds

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
