import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import and_, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.checks import CheckResult as CheckResultModel
from rest_assured.src.models.services import Service
from rest_assured.src.schemas.metrics import ServiceSummaryItem
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

            session = self._session_factory()
            try:
                result = await session.exec(
                    select(CheckResultModel)
                    .where(CheckResultModel.service_id == service_id)
                    .order_by(col(CheckResultModel.checked_at).asc())
                )
                checks = cast(list[MetricsCheckResult], list(result.all()))
            finally:
                await session.close()

            uptime_seconds = compute_current_uptime(checks)
            sla_pct = round(compute_sla(checks) * 100.0, 2)
            self._cache[service_id] = (uptime_seconds, sla_pct, self._now())
            return uptime_seconds, sla_pct

    async def get_summary(self) -> list[ServiceSummaryItem]:
        last_checks = (
            select(
                col(CheckResultModel.service_id).label("service_id"),
                col(CheckResultModel.checked_at).label("checked_at"),
                col(CheckResultModel.is_up).label("is_up"),
                func.row_number()
                .over(
                    partition_by=col(CheckResultModel.service_id),
                    order_by=col(CheckResultModel.checked_at).desc(),
                )
                .label("rn"),
            )
            .subquery()
        )

        session = self._session_factory()
        try:
            result = await session.exec(
                select(Service, last_checks.c.checked_at, last_checks.c.is_up)
                .outerjoin(
                    last_checks,
                    and_(
                        last_checks.c.service_id == Service.id,
                        last_checks.c.rn == 1,
                    ),
                )
                .where(col(Service.is_active).is_(True))
                .order_by(col(Service.id).asc())
            )
            rows = result.all()
        finally:
            await session.close()

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

    def _is_fresh(self, cached_at: datetime) -> bool:
        age = (self._now() - cached_at).total_seconds()
        return age < self._cache_ttl_seconds

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
