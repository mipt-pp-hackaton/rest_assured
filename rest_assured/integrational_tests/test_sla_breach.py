"""Integration tests for SLA-breach trigger (T4.6)."""

from datetime import datetime, timedelta, timezone

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
async def test_no_breach_when_sla_ok(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=99.0,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Добавим успешные проверки, чтобы SLA был 100%
    for _ in range(5):
        c = CheckResult(
            service_id=s.id,
            is_up=True,
            http_status=200,
            latency_ms=10,
            checked_at=datetime.now(timezone.utc),
        )
        session.add(c)
    await session.commit()

    prev = await _mailhog_total()
    check = CheckResult(
        service_id=s.id,
        is_up=True,
        http_status=200,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    # Нет breach инцидентов
    breaches = (
        await session.exec(
            select(Incident).where(Incident.service_id == s.id, Incident.sla_breach.is_(True))
        )
    ).all()
    assert len(breaches) == 0
    assert await _mailhog_total() - prev == 0


@pytest.mark.asyncio
async def test_sla_drops_creates_breach(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=99.0,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Создаём «плохую» историю: 10 фейлов подряд, чтобы SLA стал < target
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(10):
        c = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=base + timedelta(seconds=i * 10),
            error="error",
        )
        session.add(c)
    await session.commit()

    prev = await _mailhog_total()
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

    # Должен появиться breach-инцидент
    breach = (
        await session.exec(
            select(Incident).where(
                Incident.service_id == s.id,
                Incident.sla_breach.is_(True),
                Incident.closed_at.is_(None),
            )
        )
    ).first()
    assert breach is not None
    # Одно письмо sla_breach
    log = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.incident_id == breach.id, NotificationLog.kind == "sla_breach"
            )
        )
    ).first()
    assert log is not None
    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_breach_not_repeated(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=99.0,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Предыстория: SLA уже низкий
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(10):
        c = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=base + timedelta(seconds=i * 10),
            error="err",
        )
        session.add(c)
    await session.commit()

    # Первый вызов создаст breach
    check1 = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="err",
    )
    await handle_check_result(
        check1,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )
    prev = await _mailhog_total()

    # Ещё несколько вызовов при том же состоянии
    for _ in range(3):
        check = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=datetime.now(timezone.utc),
            error="err",
        )
        await handle_check_result(
            check,
            session_factory=lambda: session,
            email_sender=email_sender,
            notifications_config=notifications_config,
        )

    # Только один breach-инцидент и одно письмо
    breaches = (
        await session.exec(
            select(Incident).where(Incident.service_id == s.id, Incident.sla_breach.is_(True))
        )
    ).all()
    assert len(breaches) == 1
    logs = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.incident_id == breaches[0].id, NotificationLog.kind == "sla_breach"
            )
        )
    ).all()
    assert len(logs) == 1
    assert await _mailhog_total() - prev == 0


@pytest.mark.asyncio
async def test_breach_closes_when_sla_recovers(
    postgres_connection, email_sender, notifications_config
):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=99.0,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Создаём открытый breach-инцидент вручную
    breach = Incident(
        service_id=s.id,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        sla_breach=True,
        last_error="SLA 50% < target 99%",
    )
    session.add(breach)
    await session.commit()
    await session.refresh(breach)

    prev = await _mailhog_total()
    # Теперь эмулируем успешный check и хороший SLA (предварительно добавим много успешных проверок)
    base = datetime.now(timezone.utc) - timedelta(minutes=60)
    for i in range(100):
        c = CheckResult(
            service_id=s.id,
            is_up=True,
            http_status=200,
            latency_ms=10,
            checked_at=base + timedelta(seconds=i * 30),
        )
        session.add(c)
    await session.commit()

    check = CheckResult(
        service_id=s.id,
        is_up=True,
        http_status=200,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    await session.refresh(breach)
    assert breach.closed_at is not None
    # SLA-инцидент закрывается без отправки отдельного уведомления
    assert await _mailhog_total() - prev == 0


@pytest.mark.asyncio
async def test_new_breach_after_recovery(postgres_connection, email_sender, notifications_config):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=99.0,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Закрытый breach инцидент
    old_breach = Incident(
        service_id=s.id,
        opened_at=datetime.now(timezone.utc) - timedelta(hours=1),
        closed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        sla_breach=True,
    )
    session.add(old_breach)
    await session.commit()

    # Плохая история
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(10):
        c = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=base + timedelta(seconds=i * 10),
            error="err",
        )
        session.add(c)
    await session.commit()

    prev = await _mailhog_total()
    check = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="err",
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    new_breach = (
        await session.exec(
            select(Incident).where(
                Incident.service_id == s.id,
                Incident.sla_breach.is_(True),
                Incident.closed_at.is_(None),
            )
        )
    ).first()
    assert new_breach is not None
    assert new_breach.id != old_breach.id
    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_sla_breach_disabled_when_no_target(
    postgres_connection, email_sender, notifications_config
):
    session = postgres_connection
    s = Service(
        name="svc",
        url="http://example.com",
        interval_ms=1000,
        sla_target_pct=None,
        owner_emails=["admin@example.com"],
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)

    # Плохие проверки
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(10):
        c = CheckResult(
            service_id=s.id,
            is_up=False,
            http_status=500,
            latency_ms=10,
            checked_at=base + timedelta(seconds=i * 10),
            error="err",
        )
        session.add(c)
    await session.commit()

    check = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="err",
    )
    await handle_check_result(
        check,
        session_factory=lambda: session,
        email_sender=email_sender,
        notifications_config=notifications_config,
    )

    sla_logs = (
        await session.exec(
            select(NotificationLog).where(
                NotificationLog.service_id == s.id,
                NotificationLog.kind == "sla_breach",
            )
        )
    ).all()
    assert len(sla_logs) == 0
