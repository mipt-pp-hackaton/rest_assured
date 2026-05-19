"""Shared FastAPI dependency providers."""

from typing import Annotated

from fastapi import Depends, Request

from rest_assured.src.services.metrics_service import MetricsService


def get_metrics_service(request: Request) -> MetricsService:
    return request.app.state.metrics_service


MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
