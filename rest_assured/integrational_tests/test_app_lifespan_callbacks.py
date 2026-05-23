"""Интеграционные тесты регистрации callback'а handle_check_result (T4.7)."""

from datetime import datetime, timezone

import pytest
from sqlmodel import select
from starlette.testclient import TestClient

from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.smtp import SmtpConfig
from rest_assured.src.main import app
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.services import Service
from rest_assured.src.services.incidents import IncidentsService
from rest_assured.src.services.notifications.email import EmailSender
from rest_assured.src.services.scheduler.runner import SchedulerRunner


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


@pytest.mark.asyncio
async def test_callback_registered_on_startup(override_auth):
    """После старта приложения коллбэк зарегистрирован в SchedulerRunner."""
    with TestClient(app) as client:
        # Отправляем запрос, чтобы lifespan точно выполнился
        response = client.get("/api/health/scheduler")
        assert response.status_code == 200
    # После выхода из with lifespan завершён, состояние доступно
    runner = app.state.runner
    assert len(runner._callbacks) == 1, f"Ожидался 1 коллбэк, получено {len(runner._callbacks)}"


@pytest.mark.asyncio
async def test_end_to_end_incident_email(postgres_connection, email_sender, notifications_config):
    """
    End-to-end: создаём сервис, регистрируем callback в планировщике,
    дёргаем fire_callbacks с фейковым CheckResult и проверяем письмо в Mailhog.
    """
    session = postgres_connection
    # Добавляем тестовый сервис
    svc = Service(
        name="e2e_callback_test",
        url="http://example.com",
        interval_ms=1000,
        owner_emails=["admin@example.com"],
    )
    session.add(svc)
    await session.commit()
    await session.refresh(svc)

    # Фейковый CheckResult (как после реальной проверки)
    check = CheckResult(
        service_id=svc.id,
        is_up=False,
        http_status=500,
        latency_ms=10,
        checked_at=datetime.now(timezone.utc),
        error="test error",
    )

    # Создаём планировщик и регистрируем callback (как в lifespan)
    runner = SchedulerRunner()

    async def _callback(chk: CheckResult) -> None:
        await IncidentsService(session).handle_check_result(
            chk,
            email_sender=email_sender,
            notifications_config=notifications_config,
        )

    runner.register_callback(_callback)

    # Вызываем fire_callbacks напрямую – это триггерит наш callback и отправку письма
    await runner.fire_callbacks(check)

    # Проверяем, что создан инцидент
    incident = (await session.exec(select(Incident).where(Incident.service_id == svc.id))).first()
    assert incident is not None, "Инцидент не был создан"
    assert incident.closed_at is None

    # Проверяем, что письмо ушло в Mailhog
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8025/api/v2/messages")
        data = resp.json()
    assert data["total"] > 0, "Письмо не обнаружено в Mailhog"
