from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.repositories.services import (
    create_service,
    delete_service,
    fetch_all_services,
    fetch_service,
    notify_service_changed,
    update_service,
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
        service = await create_service(
            self._session, data=data.model_dump(exclude_unset=True)
        )
        return ServiceRead.model_validate(service)

    async def update(self, service_id: int, data: ServiceUpdate) -> ServiceRead | None:
        service = await update_service(
            self._session, service_id, updates=data.model_dump(exclude_unset=True)
        )
        if service is None:
            return None
        await notify_service_changed(self._session, service_id, "upsert")
        return ServiceRead.model_validate(service)

    async def delete(self, service_id: int) -> bool:
        found = await delete_service(self._session, service_id)
        if not found:
            return False
        await notify_service_changed(self._session, service_id, "delete")
        return True
