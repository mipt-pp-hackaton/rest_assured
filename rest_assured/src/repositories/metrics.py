from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Row, and_, func, text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service


async def fetch_checks_for_service(session: AsyncSession, service_id: int) -> Sequence[CheckResult]:
    result = await session.exec(
        select(CheckResult)
        .where(CheckResult.service_id == service_id)
        .order_by(col(CheckResult.checked_at).asc())
    )
    return result.all()


async def fetch_active_services_with_last_check(
    session: AsyncSession,
) -> Sequence[tuple[Service, datetime | None, bool | None]]:
    last_checks = select(
        col(CheckResult.service_id).label("service_id"),
        col(CheckResult.checked_at).label("checked_at"),
        col(CheckResult.is_up).label("is_up"),
        func.row_number()
        .over(
            partition_by=col(CheckResult.service_id),
            order_by=col(CheckResult.checked_at).desc(),
        )
        .label("rn"),
    ).subquery()
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
    return result.all()


async def fetch_timeseries_buckets(
    session: AsyncSession,
    service_id: int,
    from_: datetime,
    to: datetime,
    bucket_seconds: int,
) -> Sequence[Row[Any]]:
    # session.execute() intentional here: raw SQL with aggregate aliases,
    # no ORM model to return.
    result = await session.execute(  # type: ignore[call-overload]
        text(
            """
            SELECT
              date_trunc('second',
                to_timestamp(floor(extract(epoch from checked_at) / :bucket) * :bucket)
              ) AS bucket_start,
              count(*) AS checks_total,
              count(*) FILTER (WHERE is_up) AS checks_up,
              avg(latency_ms) AS latency_avg_ms,
              percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS latency_p95_ms
            FROM check_results
            WHERE service_id = :service_id
              AND checked_at >= :from
              AND checked_at < :to
            GROUP BY 1
            ORDER BY 1 ASC
            """
        ),
        {
            "service_id": service_id,
            "from": from_,
            "to": to,
            "bucket": bucket_seconds,
        },
    )
    return result.all()
