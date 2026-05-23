from fastapi import APIRouter, Depends, HTTPException, status

from rest_assured.src.api.dependencies import CatalogServiceDep
from rest_assured.src.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate
from rest_assured.src.services.auth.dependencies import get_current_active_user

router = APIRouter(
    prefix="/api/services",
    tags=["services"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/", response_model=list[ServiceRead])
async def list_services_endpoint(catalog: CatalogServiceDep) -> list[ServiceRead]:
    return await catalog.list_all()


@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service_endpoint(
    data: ServiceCreate,
    catalog: CatalogServiceDep,
) -> ServiceRead:
    return await catalog.create(data)


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service_endpoint(service_id: int, catalog: CatalogServiceDep) -> ServiceRead:
    service = await catalog.get(service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service_endpoint(
    service_id: int,
    data: ServiceUpdate,
    catalog: CatalogServiceDep,
) -> ServiceRead:
    service = await catalog.update(service_id, data)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_endpoint(
    service_id: int,
    catalog: CatalogServiceDep,
) -> None:
    found = await catalog.delete(service_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
