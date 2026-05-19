from rest_assured.src.models.services import Service
from rest_assured.src.repositories.services import (
    fetch_all_services,
    fetch_service,
    notify_service_changed,
)
from rest_assured.src.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate


async def list_services(session_factory) -> list[ServiceRead]:
    session = session_factory()
    try:
        services = await fetch_all_services(session)
        return [ServiceRead.model_validate(s) for s in services]
    finally:
        await session.close()


async def get_service(session_factory, service_id: int) -> ServiceRead | None:
    session = session_factory()
    try:
        service = await fetch_service(session, service_id)
        return ServiceRead.model_validate(service) if service else None
    finally:
        await session.close()


async def create_service(session_factory, data: ServiceCreate) -> ServiceRead:
    session = session_factory()
    try:
        service = Service(**data.model_dump(exclude_unset=True))
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return ServiceRead.model_validate(service)
    finally:
        await session.close()


async def update_service(
    session_factory, service_id: int, data: ServiceUpdate
) -> ServiceRead | None:
    session = session_factory()
    try:
        service = await fetch_service(session, service_id)
        if service is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(service, field, value)
        session.add(service)
        await session.commit()
        await session.refresh(service)
        result = ServiceRead.model_validate(service)
    finally:
        await session.close()

    await _send_notification(session_factory, service_id, "upsert")
    return result


async def delete_service(session_factory, service_id: int) -> bool:
    session = session_factory()
    try:
        service = await fetch_service(session, service_id)
        if service is None:
            return False
        await session.delete(service)
        await session.commit()
    finally:
        await session.close()

    await _send_notification(session_factory, service_id, "delete")
    return True


async def _send_notification(session_factory, service_id: int, action: str) -> None:
    session = session_factory()
    try:
        await notify_service_changed(session, service_id, action)
    finally:
        await session.close()
