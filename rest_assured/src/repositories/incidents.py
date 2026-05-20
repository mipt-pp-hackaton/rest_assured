from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.services import Service


async def fetch_incidents(
    session: AsyncSession,
    *,
    service_id: int | None = None,
    open: bool | None = None,
    sla_breach: bool | None = None,
    limit: int = 100,
) -> Sequence[Any]:
    query = select(Incident, Service.name).join(Service)

    if service_id is not None:
        query = query.where(Incident.service_id == service_id)
    if open is True:
        query = query.where(Incident.closed_at.is_(None))
    elif open is False:
        query = query.where(Incident.closed_at.isnot(None))
    if sla_breach is not None:
        query = query.where(Incident.sla_breach == sla_breach)

    query = query.order_by(Incident.opened_at.desc()).limit(limit)
    result = await session.exec(query)
    return result.all()


async def find_open_incident(
    session: AsyncSession, service_id: int, *, sla_breach: bool
) -> Incident | None:
    result = await session.exec(
        select(Incident).where(
            Incident.service_id == service_id,
            Incident.closed_at.is_(None),
            Incident.sla_breach.is_(sla_breach),
        )
    )
    return result.first()


async def create_incident(
    session: AsyncSession,
    *,
    service_id: int,
    opened_at: datetime,
    sla_breach: bool,
    last_error: str | None,
) -> Incident:
    incident = Incident(
        service_id=service_id,
        opened_at=opened_at,
        sla_breach=sla_breach,
        last_error=last_error,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


async def close_incident(
    session: AsyncSession, incident: Incident, closed_at: datetime
) -> None:
    incident.closed_at = closed_at
    session.add(incident)
    await session.commit()
