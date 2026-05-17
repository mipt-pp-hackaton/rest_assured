"""Integration tests for incident state machine (T4.5)."""

from datetime import datetime, timezone

import pytest
from sqlmodel import select

from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.smtp import SmtpConfig
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.notifications import NotificationLog
from rest_assured.src.models.services import Service
from rest_assured.src.notifications.email import EmailSender
from rest_assured.src.services.incidents import handle_check_result


@pytest.fixture
def smtp_config():
    return SmtpConfig(
        host="localhost",
        port=1025,
        user="",
        password="",
        use_tls=False,
        from_email="noreply@example.com",
        from_name="Test Sender",
    )


@pytest.fixture
def email_sender(smtp_config):
    return EmailSender(smtp_config)


@pytest.fixture
def notifications_config():
    return NotificationsConfig(enabled=True, reminder_cooldown_minutes=0)


async def _mailhog_total():
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8025/api/v2/messages")
        return resp.json()["total"]


@pytest.mark.asyncio
async def test_ok_to_fail(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    check = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="test error",
    )
    session.add(check)
    await session.commit()

    prev = await _mailhog_total()
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    incident = (await session.exec(select(Incident).where(Incident.service_id == s.id))).first()
    assert incident is not None
    assert incident.closed_at is None
    assert incident.last_error == "test error"

    log = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.incident_id == incident.id,
                NotificationLog.kind == "incident_opened",
            )
        )
    ).first()
    assert log is not None
    assert log.error is None

    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_fail_to_fail_dedup(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    incident = Incident(
        service_id=s.id, opened_at=datetime.now(timezone.utc), last_error="first error"
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    notifications_config.reminder_cooldown_minutes = 10
    prev = await _mailhog_total()

    for i in range(5):
        check = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=datetime.now(timezone.utc),
            error=f"error {i}",
        )
        await handle_check_result(
            check,
            session_factory=lambda: session,
            email_sender=email_sender,
            notifications_config=notifications_config,
        )

    incidents = (await session.exec(select(Incident).where(Incident.service_id == s.id))).all()
    assert len(incidents) == 1

    logs = (
        await session.exec(
            select(NotificationLog).where(NotificationLog.incident_id == incident.id)
        )
    ).all()

    opened_logs = [entry for entry in logs if entry.kind == "incident_opened"]
    assert len(opened_logs) == 1
    reminders = [entry for entry in logs if entry.kind == "incident_reminder"]
    assert len(reminders) == 0

    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_fail_to_fail_reminder(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    incident = Incident(
        service_id=s.id, opened_at=datetime.now(timezone.utc), last_error="first error"
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    notifications_config.reminder_cooldown_minutes = 0
    prev = await _mailhog_total()

    check = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="second error",
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    log = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.incident_id == incident.id,
                NotificationLog.kind == "incident_reminder",
            )
        )
    ).first()
    assert log is not None

    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_fail_to_ok(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    incident = Incident(
        service_id=s.id, opened_at=datetime.now(timezone.utc), last_error="error"
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    prev = await _mailhog_total()

    check = CheckResult(
        service_id=s.id,
        is_up=True,
        http_status=200,
        latency_ms=5,
        checked_at=datetime.now(timezone.utc),
        error=None,
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    await session.refresh(incident)
    assert incident.closed_at is not None

    log = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.incident_id == incident.id,
                NotificationLog.kind == "incident_closed",
            )
        )
    ).first()
    assert log is not None

    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_ok_to_ok(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    prev = await _mailhog_total()

    check = CheckResult(
        service_id=s.id,
        is_up=True,
        http_status=200,
        latency_ms=5,
        checked_at=datetime.now(timezone.utc),
        error=None,
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    incidents = (
        await session.exec(
            select(Incident).where(Incident.service_id == s.id)
        )
    ).all()
    assert len(incidents) == 0
    logs = (
        await session.exec(
            select(NotificationLog).where(NotificationLog.service_id == s.id)
        )
    ).all()
    assert len(logs) == 0
    assert await _mailhog_total() - prev == 0


@pytest.mark.asyncio
async def test_smtp_failure_incident_still_created(
    postgres_connection, email_sender, notifications_config, monkeypatch
):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    async def fake_send(**kwargs):
        return False, "SMTP server error"

    monkeypatch.setattr(email_sender, "send", fake_send)

    check = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="error",
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    incident = (await session.exec(select(Incident).where(Incident.service_id == s.id))).first()
    assert incident is not None
    log = (
        await session.exec(
            select(NotificationLog).where(NotificationLog.incident_id == incident.id)
        )
    ).first()
    assert log is not None
    assert log.error is not None
