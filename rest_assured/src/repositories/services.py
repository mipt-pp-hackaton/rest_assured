import json
from collections.abc import Sequence

from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.services import Service


async def fetch_all_services(session: AsyncSession) -> Sequence[Service]:
    result = await session.exec(select(Service))
    return result.all()


async def fetch_service(session: AsyncSession, service_id: int) -> Service | None:
    return await session.get(Service, service_id)


async def notify_service_changed(session: AsyncSession, service_id: int, action: str) -> None:
    payload = json.dumps({"id": service_id, "action": action})
    # session.execute() intentional here: raw SQL, no ORM model to return
    await session.execute(  # type: ignore[call-overload]
        text("SELECT pg_notify('service_changed', :payload)"),
        {"payload": payload},
    )
    await session.commit()
