"""Shared FastAPI dependency providers."""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.repositories.database_session import get_session_dependency
from rest_assured.src.services.auth import AuthService
from rest_assured.src.services.catalog import CatalogService
from rest_assured.src.services.incidents import IncidentsService
from rest_assured.src.services.metrics_service import MetricsService

# Re-export under the historical name so existing consumers (and FastAPI
# `dependency_overrides[get_db_session]` patches in tests) keep working.
get_db_session = get_session_dependency


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_catalog_service(session: DbSession) -> CatalogService:
    return CatalogService(session)


def get_incidents_service(session: DbSession) -> IncidentsService:
    return IncidentsService(session)


def get_metrics_service(session: DbSession) -> MetricsService:
    return MetricsService(session)


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
IncidentsServiceDep = Annotated[IncidentsService, Depends(get_incidents_service)]
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
