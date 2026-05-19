from fastapi import APIRouter, Depends, HTTPException, Request, status

from rest_assured.src.models.users import User
from rest_assured.src.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate
from rest_assured.src.services.auth.dependencies import get_current_user
from rest_assured.src.services.catalog import (
    create_service,
    delete_service,
    get_service,
    list_services,
    update_service,
)

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/", response_model=list[ServiceRead])
async def list_services_endpoint(request: Request) -> list[ServiceRead]:
    return await list_services(request.app.state.session_factory)


@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service_endpoint(
    data: ServiceCreate,
    request: Request,
    _: User = Depends(get_current_user),
) -> ServiceRead:
    return await create_service(request.app.state.session_factory, data)


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service_endpoint(service_id: int, request: Request) -> ServiceRead:
    service = await get_service(request.app.state.session_factory, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service_endpoint(
    service_id: int,
    data: ServiceUpdate,
    request: Request,
    _: User = Depends(get_current_user),
) -> ServiceRead:
    service = await update_service(request.app.state.session_factory, service_id, data)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_endpoint(
    service_id: int,
    request: Request,
    _: User = Depends(get_current_user),
) -> None:
    found = await delete_service(request.app.state.session_factory, service_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
