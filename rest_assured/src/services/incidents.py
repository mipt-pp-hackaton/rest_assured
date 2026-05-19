"""State machine for incident management (OK↔FAIL) with dedup and reminders."""

import logging
from datetime import timedelta

from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service
from rest_assured.src.repositories.checks import fetch_checks_since
from rest_assured.src.repositories.incidents import (
    close_incident,
    create_incident,
    fetch_incidents,
    find_open_incident,
)
from rest_assured.src.repositories.notifications import (
    create_notification_log,
    fetch_last_notification_at,
)
from rest_assured.src.repositories.services import fetch_service
from rest_assured.src.schemas.incidents import IncidentRead
from rest_assured.src.services.metrics import compute_sla
from rest_assured.src.services.notifications.email import EmailSender

logger = logging.getLogger(__name__)


class IncidentsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(
        self,
        *,
        service_id: int | None = None,
        open: bool | None = None,
        sla_breach: bool | None = None,
        limit: int = 100,
    ) -> list[IncidentRead]:
        rows = await fetch_incidents(
            self._session,
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
                    int((inc.closed_at - inc.opened_at).total_seconds()) if inc.closed_at else None
                ),
            )
            for inc, name in rows
        ]

    async def handle_check_result(
        self,
        check: CheckResult,
        *,
        email_sender: EmailSender,
        notifications_config: NotificationsConfig,
    ) -> None:
        if not notifications_config.enabled:
            return
        try:
            service = await fetch_service(self._session, check.service_id)
            if service is None:
                return
            to_emails = service.owner_emails

            # Если задана цель SLA – работаем только с SLA‑брешью
            if service.sla_target_pct is not None:
                await self._handle_sla_breach(check, service, to_emails, email_sender)
                return

            open_incident = await find_open_incident(
                self._session, check.service_id, sla_breach=False
            )

            if not check.is_up:
                if open_incident is None:
                    incident = await create_incident(
                        self._session,
                        service_id=check.service_id,
                        opened_at=check.checked_at,
                        sla_breach=False,
                        last_error=check.error,
                    )
                    ok, err = await email_sender.send(
                        to=to_emails,
                        kind="incident_opened",
                        context={"service": service, "incident": incident, "check": check},
                    )
                    await create_notification_log(
                        self._session,
                        incident_id=incident.id,
                        service_id=service.id,
                        kind="incident_opened",
                        success=ok,
                        error_msg=err,
                        recipients=to_emails,
                    )
                else:
                    last_reminder = await fetch_last_notification_at(
                        self._session, open_incident.id, "incident_reminder"
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
                        await create_notification_log(
                            self._session,
                            incident_id=open_incident.id,
                            service_id=service.id,
                            kind="incident_reminder",
                            success=ok,
                            error_msg=err,
                            recipients=to_emails,
                        )
            else:
                if open_incident is not None:
                    await close_incident(self._session, open_incident, check.checked_at)
                    ok, err = await email_sender.send(
                        to=to_emails,
                        kind="incident_closed",
                        context={"service": service, "incident": open_incident, "check": check},
                    )
                    await create_notification_log(
                        self._session,
                        incident_id=open_incident.id,
                        service_id=service.id,
                        kind="incident_closed",
                        success=ok,
                        error_msg=err,
                        recipients=to_emails,
                    )

        except Exception:
            logger.exception("handle_check_result failed for check_id=%s", check.id)

    async def _handle_sla_breach(
        self,
        check: CheckResult,
        service: Service,
        to_emails: list[str],
        email_sender: EmailSender,
    ) -> None:
        since = check.checked_at - timedelta(hours=24)
        checks = await fetch_checks_since(self._session, check.service_id, since)
        sla_pct = compute_sla(list(checks)) * 100.0 if checks else 100.0

        active_breach = await find_open_incident(
            self._session, service.id, sla_breach=True
        )
        if sla_pct < service.sla_target_pct:
            if active_breach is None:
                inc = await create_incident(
                    self._session,
                    service_id=service.id,
                    opened_at=check.checked_at,
                    sla_breach=True,
                    last_error=f"SLA {sla_pct:.2f}% < target {service.sla_target_pct}%",
                )
                ok, err = await email_sender.send(
                    to=to_emails,
                    kind="sla_breach",
                    context={
                        "service": service,
                        "sla_pct": sla_pct,
                        "target": service.sla_target_pct,
                    },
                )
                await create_notification_log(
                    self._session,
                    incident_id=inc.id,
                    service_id=service.id,
                    kind="sla_breach",
                    success=ok,
                    error_msg=err,
                    recipients=to_emails,
                )
        else:
            if active_breach is not None:
                await close_incident(self._session, active_breach, check.checked_at)
