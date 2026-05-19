from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text

from rest_assured.src.models.services import Service
from rest_assured.src.schemas.metrics import (
    ServiceMetricsResponse,
    ServiceSummaryItem,
    TimeseriesBucket,
)
from rest_assured.src.services.metrics_service import MetricsService

router = APIRouter(prefix="/api/services", tags=["metrics"])


def get_metrics_service(request: Request) -> MetricsService:
    return request.app.state.metrics_service


@router.get("/summary", response_model=list[ServiceSummaryItem])
async def get_services_summary(
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> list[ServiceSummaryItem]:
    return await metrics_service.get_summary()


@router.get("/{service_id}/metrics", response_model=ServiceMetricsResponse)
async def get_service_metrics(
    service_id: int,
    request: Request,
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> ServiceMetricsResponse:
    session = request.app.state.session_factory()
    try:
        service = await session.get(Service, service_id)
    finally:
        await session.close()

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")

    uptime_seconds, sla_pct = await metrics_service.get_metrics(service_id)
    return ServiceMetricsResponse(
        service_id=service_id,
        current_uptime_seconds=uptime_seconds,
        sla_pct=sla_pct,
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/{service_id}/timeseries", response_model=list[TimeseriesBucket])
async def get_service_timeseries(
    service_id: int,
    request: Request,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    bucket_seconds: int = Query(60, ge=10, le=3600),
) -> list[TimeseriesBucket]:
    if to <= from_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to must be greater than from",
        )

    session = request.app.state.session_factory()
    try:
        service = await session.get(Service, service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")

        result = await session.exec(
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
            params={
                "service_id": service_id,
                "from": from_,
                "to": to,
                "bucket": bucket_seconds,
            },
        )
        rows = result.all()
    finally:
        await session.close()

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
