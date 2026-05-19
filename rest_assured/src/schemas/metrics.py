from datetime import datetime

from pydantic import BaseModel


class ServiceMetricsResponse(BaseModel):
    service_id: int
    current_uptime_seconds: int
    sla_pct: float
    computed_at: datetime


class ServiceSummaryItem(BaseModel):
    service_id: int
    name: str
    url: str
    is_active: bool
    current_uptime_seconds: int
    sla_pct: float
    last_check_at: datetime | None
    last_check_is_up: bool | None


class TimeseriesBucket(BaseModel):
    bucket_start: datetime
    checks_total: int
    checks_up: int
    up_ratio: float
    latency_avg_ms: float | None
    latency_p95_ms: float | None
