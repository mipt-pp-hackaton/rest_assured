from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import select

from rest_assured.src.auth.dependencies import get_current_user
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.services import Service
from rest_assured.src.models.users import User
from rest_assured.src.repositories.database_session import get_session

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class IncidentRead(BaseModel):
    id: int
    service_id: int
    service_name: str
    opened_at: datetime
    closed_at: datetime | None
    last_error: str | None
    sla_breach: bool
    duration_seconds: int | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    service_id: int | None = Query(None),
    open: bool | None = Query(None, description="true — только открытые, false — только закрытые"),
    sla_breach: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(get_current_user),
) -> list[IncidentRead]:
    session = get_session()
    try:
        query = select(Incident, Service.name).join(Service, Incident.service_id == Service.id)

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
        rows = result.all()

        return [
            IncidentRead(
                id=inc.id,
                service_id=inc.service_id,
                service_name=name,
                opened_at=inc.opened_at,
                closed_at=inc.closed_at,
                last_error=inc.last_error,
                sla_breach=inc.sla_breach,
                duration_seconds=(
                    int((inc.closed_at - inc.opened_at).total_seconds()) if inc.closed_at else None
                ),
            )
            for inc, name in rows
        ]
    finally:
        await session.close()
