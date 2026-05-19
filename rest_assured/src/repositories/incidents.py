from collections.abc import Sequence
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
