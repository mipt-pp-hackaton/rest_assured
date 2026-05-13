"""Интеграционные тесты моделей Incident и NotificationLog."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.notifications import NotificationLog
from rest_assured.src.models.services import Service


@pytest.mark.asyncio
async def test_create_incident(postgres_connection):
    service = Service(name="svc1", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    now = datetime.now(timezone.utc)
    incident = Incident(
        service_id=service.id, opened_at=now, last_error="test error",
    )
    postgres_connection.add(incident)
    await postgres_connection.commit()
    await postgres_connection.refresh(incident)

    assert incident.id is not None
    assert incident.service_id == service.id
    assert incident.closed_at is None
    assert incident.last_error == "test error"
    assert incident.sla_breach is False


@pytest.mark.asyncio
async def test_unique_open_incident_per_service(postgres_connection):
    service = Service(name="svc2", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    inc1 = Incident(service_id=service.id, opened_at=datetime.now(timezone.utc))
    postgres_connection.add(inc1)
    await postgres_connection.commit()

    inc2 = Incident(
        service_id=service.id, opened_at=datetime.now(timezone.utc),
    )
    postgres_connection.add(inc2)
    with pytest.raises(IntegrityError):
        await postgres_connection.commit()
    await postgres_connection.rollback()


@pytest.mark.asyncio
async def test_reopen_after_close(postgres_connection):
    service = Service(name="svc3", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    inc1 = Incident(
        service_id=service.id, opened_at=datetime.now(timezone.utc),
    )
    postgres_connection.add(inc1)
    await postgres_connection.commit()
    await postgres_connection.refresh(inc1)

    inc1.closed_at = datetime.now(timezone.utc)
    await postgres_connection.commit()

    inc2 = Incident(
        service_id=service.id, opened_at=datetime.now(timezone.utc),
    )
    postgres_connection.add(inc2)
    await postgres_connection.commit()
    assert inc2.id is not None


@pytest.mark.asyncio
async def test_notification_log_creation(postgres_connection):
    service = Service(name="svc4", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    incident = Incident(
        service_id=service.id, opened_at=datetime.now(timezone.utc),
    )
    postgres_connection.add(incident)
    await postgres_connection.commit()
    await postgres_connection.refresh(incident)

    log = NotificationLog(
        incident_id=incident.id,
        service_id=service.id,
        kind="incident_opened",
        sent_at=datetime.now(timezone.utc),
        recipients="admin@example.com",
        subject="Incident opened",
    )
    postgres_connection.add(log)
    await postgres_connection.commit()
    await postgres_connection.refresh(log)

    assert log.id is not None
    assert log.kind == "incident_opened"
    assert log.error is None


@pytest.mark.asyncio
async def test_notification_log_without_incident(postgres_connection):
    """NotificationLog может существовать без привязки к инциденту."""
    service = Service(name="svc5", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    log = NotificationLog(
        incident_id=None,
        service_id=service.id,
        kind="manual_alert",
        sent_at=datetime.now(timezone.utc),
        recipients="ops@example.com",
        subject="Manual alert",
    )
    postgres_connection.add(log)
    await postgres_connection.commit()
    await postgres_connection.refresh(log)

    assert log.id is not None
    assert log.incident_id is None


@pytest.mark.asyncio
async def test_incident_sla_breach_flag(postgres_connection):
    """Проверяет установку флага sla_breach."""
    service = Service(name="svc6", url="http://example.com", interval_ms=1000)
    postgres_connection.add(service)
    await postgres_connection.commit()
    await postgres_connection.refresh(service)

    incident = Incident(
        service_id=service.id,
        opened_at=datetime.now(timezone.utc),
        sla_breach=True,
    )
    postgres_connection.add(incident)
    await postgres_connection.commit()
    await postgres_connection.refresh(incident)

    assert incident.sla_breach is True


@pytest.mark.asyncio
async def test_incident_fk_prevents_orphan(postgres_connection):
    """FK на несуществующий service_id должен бросать IntegrityError."""
    incident = Incident(
        service_id=999999,
        opened_at=datetime.now(timezone.utc),
    )
    postgres_connection.add(incident)
    with pytest.raises(IntegrityError):
        await postgres_connection.commit()
    await postgres_connection.rollback()
