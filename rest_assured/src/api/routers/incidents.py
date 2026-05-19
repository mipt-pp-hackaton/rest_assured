from fastapi import APIRouter, Depends, Query

from rest_assured.src.api.dependencies import IncidentsServiceDep
from rest_assured.src.models.users import User
from rest_assured.src.schemas.incidents import IncidentRead
from rest_assured.src.services.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
async def list_incidents_endpoint(
    incidents: IncidentsServiceDep,
    service_id: int | None = Query(None),
    open: bool | None = Query(None, description="true — только открытые, false — только закрытые"),
    sla_breach: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(get_current_user),
) -> list[IncidentRead]:
    return await incidents.list_all(
        service_id=service_id,
        open=open,
        sla_breach=sla_breach,
        limit=limit,
    )
