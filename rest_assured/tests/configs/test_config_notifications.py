"""Тесты для конфигураций SMTP и уведомлений (T4.1)."""

import pytest
from pydantic import ValidationError

from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.smtp import SmtpConfig

# ----------------------------------------------------------------
# Юнит-тесты моделей
# ----------------------------------------------------------------


def test_smtp_defaults():
    cfg = SmtpConfig(
        host="smtp.example.com",
        from_email="test@example.com",
        from_name="Test",
    )
    assert cfg.port == 1025
    assert cfg.user == ""
    assert cfg.password == ""
    assert cfg.use_tls is False


def test_smtp_invalid_email():
    with pytest.raises(ValidationError):
        SmtpConfig(host="smtp.example.com", from_email="not-an-email", from_name="Test")


def test_notifications_defaults():
    cfg = NotificationsConfig()
    assert cfg.enabled is True
    assert cfg.reminder_cooldown_minutes == 30
    assert cfg.include_runbook_link is False
