"""State machine for incident management (OK↔FAIL) with dedup and reminders."""

import logging
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.notifications import NotificationLog
from rest_assured.src.models.services import Service
from rest_assured.src.notifications.email import EmailSender

logger = logging.getLogger(__name__)


async def handle_check_result(
    check: CheckResult,
    *,
    session_factory,
    email_sender: EmailSender,
    notifications_config: NotificationsConfig,
) -> None:
    """Обрабатывает результат проверки, управляя инцидентами и уведомлениями.

    Вызывается из SchedulerRunner после записи CheckResult.
    Никогда не выбрасывает исключений наружу.
    """
    if not notifications_config.enabled:
        return
    try:
        session = session_factory()
        service = await session.get(Service, check.service_id)
        if service is None:
            return
        to_emails = service.owner_emails  # list[str]

        open_incident = await _get_open_incident(session, check.service_id)

        if not check.is_up:
            if open_incident is None:
                # OK → FAIL: создаём инцидент
                incident = Incident(
                    service_id=check.service_id,
                    opened_at=check.checked_at,
                    last_error=check.error,
                )
                session.add(incident)
                await session.commit()
                await session.refresh(incident)

                ok, err = await email_sender.send(
                    to=to_emails,
                    kind="incident_opened",
                    context={
                        "service": service,
                        "incident": incident,
                        "check": check,
                    },
                )
                await _log_notification(
                    session, incident.id, service.id, "incident_opened", ok, err, to_emails
                )
            else:
                # FAIL → FAIL: проверяем необходимость напоминания
                last_reminder = await _last_notification_at(
                    session, open_incident.id, "incident_reminder"
                )
                ref_time = last_reminder if last_reminder else open_incident.opened_at
                cooldown = notifications_config.reminder_cooldown_minutes * 60
                if (check.checked_at - ref_time).total_seconds() >= cooldown:
                    ok, err = await email_sender.send(
                        to=to_emails,
                        kind="incident_reminder",
                        context={
                            "service": service,
                            "incident": open_incident,
                            "check": check,
                        },
                    )
                    await _log_notification(
                        session,
                        open_incident.id,
                        service.id,
                        "incident_reminder",
                        ok,
                        err,
                        to_emails,
                    )
        else:
            if open_incident is not None:
                # FAIL → OK: закрываем инцидент
                open_incident.closed_at = check.checked_at
                session.add(open_incident)
                await session.commit()

                ok, err = await email_sender.send(
                    to=to_emails,
                    kind="incident_closed",
                    context={
                        "service": service,
                        "incident": open_incident,
                        "check": check,
                    },
                )
                await _log_notification(
                    session, open_incident.id, service.id, "incident_closed", ok, err, to_emails
                )
            # OK → OK: ничего не делаем
    except Exception:
        logger.exception("handle_check_result failed for check_id=%s", check.id)


# --------------- helpers ---------------

async def _get_open_incident(session: AsyncSession, service_id: int) -> Incident | None:
    result = await session.exec(
        select(Incident).where(
            Incident.service_id == service_id,
            Incident.closed_at.is_(None),
        )
    )
    return result.first()


async def _last_notification_at(
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


async def _log_notification(
    session: AsyncSession,
    incident_id: int,
    service_id: int,
    kind: str,
    success: bool,
    error_msg: str | None,
    recipients: list[str],
) -> None:
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