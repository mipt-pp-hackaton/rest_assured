from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.notifications import NotificationLog


async def fetch_last_notification_at(
    session: AsyncSession, incident_id: int, kind: str
) -> datetime | None:
    result = await session.exec(
        select(NotificationLog.sent_at)
        .where(
            NotificationLog.incident_id == incident_id,
            NotificationLog.kind == kind,
        )
        .order_by(NotificationLog.sent_at.desc())
        .limit(1)
    )
    return result.first()


async def create_notification_log(
    session: AsyncSession,
    *,
    incident_id: int,
    service_id: int,
    kind: str,
    success: bool,
    error_msg: str | None,
    recipients: list[str],
) -> NotificationLog:
    log_entry = NotificationLog(
        incident_id=incident_id,
        service_id=service_id,
        kind=kind,
        sent_at=datetime.now(timezone.utc),
        recipients=", ".join(recipients),
        subject="",
        error=error_msg if not success else None,
    )
    session.add(log_entry)
    await session.commit()
    return log_entry
