from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.services import Service
from rest_assured.src.repositories.services import (
    fetch_all_services,
    fetch_service,
    notify_service_changed,
)
from rest_assured.src.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ServiceRead]:
        services = await fetch_all_services(self._session)
        return [ServiceRead.model_validate(s) for s in services]

    async def get(self, service_id: int) -> ServiceRead | None:
        service = await fetch_service(self._session, service_id)
        return ServiceRead.model_validate(service) if service else None

    async def create(self, data: ServiceCreate) -> ServiceRead:
        service = Service(**data.model_dump(exclude_unset=True))
        self._session.add(service)
        await self._session.commit()
        await self._session.refresh(service)
        return ServiceRead.model_validate(service)

    async def update(self, service_id: int, data: ServiceUpdate) -> ServiceRead | None:
        service = await fetch_service(self._session, service_id)
        if service is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(service, field, value)
        self._session.add(service)
        await self._session.commit()
        await self._session.refresh(service)
        result = ServiceRead.model_validate(service)
        await notify_service_changed(self._session, service_id, "upsert")
        return result

    async def delete(self, service_id: int) -> bool:
        service = await fetch_service(self._session, service_id)
        if service is None:
            return False
        await self._session.delete(service)
        await self._session.commit()
        await notify_service_changed(self._session, service_id, "delete")
        return True
