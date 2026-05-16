"""Integration tests for EmailSender with Mailhog."""

import httpx
import pytest

from rest_assured.src.configs.app.smtp import SmtpConfig
from rest_assured.src.notifications.email import EmailSender


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


async def _mailhog_total():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8025/api/v2/messages")
        return resp.json()["total"]


@pytest.mark.asyncio
async def test_send_incident_opened(email_sender):
    context = {
        "service": {"name": "TestSvc", "url": "http://test.com"},
        "opened_at": "2026-01-01 12:00",
        "last_error": "Timeout",
    }
    prev = await _mailhog_total()
    ok, error = await email_sender.send(
        to=["test@example.com"],
        kind="incident_opened",
        context=context,
    )
    assert ok is True
    assert error is None
    assert await _mailhog_total() - prev == 1


@pytest.mark.asyncio
async def test_send_unknown_kind(email_sender):
    ok, error = await email_sender.send(
        to=["test@example.com"],
        kind="unknown",
        context={},
    )
    assert ok is False
    assert "TemplateNotFound" in error


@pytest.mark.asyncio
async def test_smtp_unreachable():
    bad_config = SmtpConfig(
        host="127.0.0.1",
        port=9999,
        user="",
        password="",
        use_tls=False,
        from_email="noreply@example.com",
        from_name="Test",
    )
    sender = EmailSender(bad_config)
    ok, error = await sender.send(
        to=["test@example.com"],
        kind="incident_opened",
        context={
            "service": {"name": "TestSvc", "url": "http://test.com"},
            "opened_at": "",
            "last_error": "",
        },
    )
    assert ok is False
    assert "SMTPConnectError" in error or "ConnectionError" in error or "OSError" in error
