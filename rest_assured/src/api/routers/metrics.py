from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from rest_assured.src.api.dependencies import MetricsServiceDep
from rest_assured.src.schemas.metrics import (
    ServiceMetricsResponse,
    ServiceSummaryItem,
    TimeseriesBucket,
)

router = APIRouter(prefix="/api/services", tags=["metrics"])


@router.get("/summary", response_model=list[ServiceSummaryItem])
async def get_services_summary(
    metrics_service: MetricsServiceDep,
) -> list[ServiceSummaryItem]:
    return await metrics_service.get_summary()


@router.get("/{service_id}/metrics", response_model=ServiceMetricsResponse)
async def get_service_metrics(
    service_id: int,
    metrics_service: MetricsServiceDep,
) -> ServiceMetricsResponse:
    service = await metrics_service.get_service(service_id)
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
    metrics_service: MetricsServiceDep,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    bucket_seconds: int = Query(60, ge=10, le=3600),
) -> list[TimeseriesBucket]:
    if to <= from_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to must be greater than from",
        )

    service = await metrics_service.get_service(service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")

    return await metrics_service.get_timeseries(service_id, from_, to, bucket_seconds)
