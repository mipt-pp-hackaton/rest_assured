"""Интеграционные тесты моделей Incident и NotificationLog."""
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.notifications import NotificationLog
from rest_assured.src.models.services import Service

@pytest.mark.asyncio
async def test_create_incident(postgres_connection):
    s = Service(name="svc1", url="http://example.com", interval_ms=1000)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    now = datetime.now(timezone.utc)
    incident = Incident(service_id=s.id, opened_at=now, last_error="test error")
    postgres_connection.add(incident)
    await postgres_connection.commit()
    await postgres_connection.refresh(incident)

    assert incident.id is not None
    assert incident.service_id == s.id
    assert incident.closed_at is None
    assert incident.last_error == "test error"
    assert incident.sla_breach is False

@pytest.mark.asyncio
async def test_unique_open_incident_per_service(postgres_connection):
    s = Service(name="svc2", url="http://example.com", interval_ms=1000)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    now = datetime.now(timezone.utc)
    inc1 = Incident(service_id=s.id, opened_at=now)
    postgres_connection.add(inc1)
    await postgres_connection.commit()

    inc2 = Incident(service_id=s.id, opened_at=datetime.now(timezone.utc))
    postgres_connection.add(inc2)
    with pytest.raises(IntegrityError):
        await postgres_connection.commit()
    await postgres_connection.rollback()

@pytest.mark.asyncio
async def test_reopen_after_close(postgres_connection):
    s = Service(name="svc3", url="http://example.com", interval_ms=1000)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    now = datetime.now(timezone.utc)
    inc1 = Incident(service_id=s.id, opened_at=now)
    postgres_connection.add(inc1)
    await postgres_connection.commit()
    await postgres_connection.refresh(inc1)

    # закрываем
    inc1.closed_at = datetime.now(timezone.utc)
    await postgres_connection.commit()

    # теперь можно создать новый открытый
    inc2 = Incident(service_id=s.id, opened_at=datetime.now(timezone.utc))
    postgres_connection.add(inc2)
    await postgres_connection.commit()
    assert inc2.id is not None

@pytest.mark.asyncio
async def test_notification_log_creation(postgres_connection):
    s = Service(name="svc4", url="http://example.com", interval_ms=1000)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    incident = Incident(service_id=s.id, opened_at=datetime.now(timezone.utc))
    postgres_connection.add(incident)
    await postgres_connection.commit()
    await postgres_connection.refresh(incident)

    log = NotificationLog(
        incident_id=incident.id,
        service_id=s.id,
        kind="incident_opened",
        sent_at=datetime.now(timezone.utc),
        recipients="admin@example.com",
        subject="Incident opened",
        error=None,
    )
    postgres_connection.add(log)
    await postgres_connection.commit()
    await postgres_connection.refresh(log)

    assert log.id is not None
    assert log.kind == "incident_opened"
    assert log.error is None