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
from rest_assured.src.repositories.incidents import fetch_incidents
from rest_assured.src.schemas.incidents import IncidentRead
from rest_assured.src.services.metrics import compute_sla

logger = logging.getLogger(__name__)


async def list_incidents(
    *,
    session_factory,
    service_id: int | None = None,
    open: bool | None = None,
    sla_breach: bool | None = None,
    limit: int = 100,
) -> list[IncidentRead]:
    session = session_factory()
    try:
        rows = await fetch_incidents(
            session,
            service_id=service_id,
            open=open,
            sla_breach=sla_breach,
            limit=limit,
        )
        return [
            IncidentRead(
                id=inc.id,
                service_id=inc.service_id,
                service_name=name,
                opened_at=inc.opened_at,
                closed_at=inc.closed_at,
                last_error=inc.last_error,
                sla_breach=inc.sla_breach,
                duration_seconds=(
                    int((inc.closed_at - inc.opened_at).total_seconds())
                    if inc.closed_at
                    else None
                ),
            )
            for inc, name in rows
        ]
    finally:
        await session.close()


async def handle_check_result(
    check: CheckResult,
    *,
    session_factory,
    email_sender: EmailSender,
    notifications_config: NotificationsConfig,
    metrics_service=None,
) -> None:
    if not notifications_config.enabled:
        return
    try:
        session = session_factory()
        service = await session.get(Service, check.service_id)
        if service is None:
            return
        to_emails = service.owner_emails

        # Если задана цель SLA – работаем только с SLA‑брешью
        if service.sla_target_pct is not None:
            await _handle_sla_breach(check, service, to_emails, session, email_sender)
            return

        # Иначе – старая логика обычных инцидентов (sla_breach=False)
        open_incident = await _get_open_incident(session, check.service_id)

        if not check.is_up:
            if open_incident is None:
                # OK → FAIL: создаём обычный инцидент
                incident = Incident(
                    service_id=check.service_id,
                    opened_at=check.checked_at,
                    last_error=check.error,
                    sla_breach=False,
                )
                session.add(incident)
                await session.commit()
                await session.refresh(incident)
                ok, err = await email_sender.send(
                    to=to_emails,
                    kind="incident_opened",
                    context={"service": service, "incident": incident, "check": check},
                )
                await _log_notification(
                    session, incident.id, service.id, "incident_opened", ok, err, to_emails
                )
            else:
                last_reminder = await _last_notification_at(
                    session, open_incident.id, "incident_reminder"
                )
                ref_time = last_reminder if last_reminder else open_incident.opened_at
                cooldown = notifications_config.reminder_cooldown_minutes * 60
                if (check.checked_at - ref_time).total_seconds() >= cooldown:
                    ok, err = await email_sender.send(
                        to=to_emails,
                        kind="incident_reminder",
                        context={"service": service, "incident": open_incident, "check": check},
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
                # FAIL → OK: закрываем обычный инцидент
                open_incident.closed_at = check.checked_at
                session.add(open_incident)
                await session.commit()
                ok, err = await email_sender.send(
                    to=to_emails,
                    kind="incident_closed",
                    context={"service": service, "incident": open_incident, "check": check},
                )
                await _log_notification(
                    session, open_incident.id, service.id, "incident_closed", ok, err, to_emails
                )

    except Exception:
        logger.exception("handle_check_result failed for check_id=%s", check.id)


async def _handle_sla_breach(check, service, to_emails, session, email_sender):
    from datetime import timedelta

    since = check.checked_at - timedelta(hours=24)
    checks_result = await session.exec(
        select(CheckResult)
        .where(CheckResult.service_id == check.service_id)
        .where(CheckResult.checked_at >= since)
        .order_by(CheckResult.checked_at.asc())
    )
    checks = checks_result.all()
    sla_pct = compute_sla(checks) * 100.0 if checks else 100.0

    active_breach = await _get_open_sla_breach_incident(session, service.id)
    if sla_pct < service.sla_target_pct:
        if active_breach is None:
            inc = Incident(
                service_id=service.id,
                opened_at=check.checked_at,
                sla_breach=True,
                last_error=f"SLA {sla_pct:.2f}% < target {service.sla_target_pct}%",
            )
            session.add(inc)
            await session.commit()
            await session.refresh(inc)
            ok, err = await email_sender.send(
                to=to_emails,
                kind="sla_breach",
                context={"service": service, "sla_pct": sla_pct, "target": service.sla_target_pct},
            )
            await _log_notification(session, inc.id, service.id, "sla_breach", ok, err, to_emails)
    else:
        if active_breach is not None:
            active_breach.closed_at = check.checked_at
            session.add(active_breach)
            await session.commit()


# --------------- helpers ---------------


async def _get_open_incident(session: AsyncSession, service_id: int) -> Incident | None:
    """Обычный открытый инцидент (не SLA-брешь)."""
    result = await session.exec(
        select(Incident).where(
            Incident.service_id == service_id,
            Incident.closed_at.is_(None),
            Incident.sla_breach.is_(False),  # <-- только обычные
        )
    )
    return result.first()


async def _get_open_sla_breach_incident(session: AsyncSession, service_id: int) -> Incident | None:
    """Открытый SLA‑брешь инцидент."""
    result = await session.exec(
        select(Incident).where(
            Incident.service_id == service_id,
            Incident.sla_breach.is_(True),
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
