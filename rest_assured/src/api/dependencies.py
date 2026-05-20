"""Shared FastAPI dependency providers."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.services.auth import AuthService
from rest_assured.src.services.catalog import CatalogService
from rest_assured.src.services.incidents import IncidentsService
from rest_assured.src.services.metrics_service import MetricsService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = get_session()
    try:
        yield session
    finally:
        await session.close()


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
