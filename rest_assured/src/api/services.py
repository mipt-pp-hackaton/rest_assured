import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel import select

from rest_assured.src.auth.jwt import get_current_user
from rest_assured.src.models.services import Service
from rest_assured.src.models.user import User
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate

services_router = APIRouter(prefix="/api/services", tags=["services"])


@services_router.get("/", response_model=list[ServiceRead])
async def list_services():
    session = get_session()
    try:
        result = await session.exec(select(Service))
        return result.all()
    finally:
        await session.close()


@services_router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    current_user: User = Depends(get_current_user),
):
    session = get_session()
    try:
        service = Service(**data.model_dump(exclude_unset=True))
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service
    finally:
        await session.close()


@services_router.get("/{service_id}", response_model=ServiceRead)
async def get_service(service_id: int):
    session = get_session()
    try:
        service = await session.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        return service
    finally:
        await session.close()


async def _notify_service_changed(service_id: int, action: str) -> None:
    session = get_session()
    try:
        payload = json.dumps({"id": service_id, "action": action})
        await session.exec(
            text("SELECT pg_notify('service_changed', :payload)"),
            {"payload": payload},
        )
        await session.commit()
    finally:
        await session.close()


@services_router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    current_user: User = Depends(get_current_user),
):
    session = get_session()
    try:
        service = await session.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)
        session.add(service)
        await session.commit()
        await session.refresh(service)
    finally:
        await session.close()

    await _notify_service_changed(service_id, "upsert")
    return service


@services_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int,
    current_user: User = Depends(get_current_user),
):
    session = get_session()
    try:
        service = await session.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        await session.delete(service)
        await session.commit()
    finally:
        await session.close()

    await _notify_service_changed(service_id, "delete")
