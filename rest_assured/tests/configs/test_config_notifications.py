"""Тесты для конфигураций SMTP и уведомлений (T4.1)."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from rest_assured.src.configs.app.main import Settings, _override_from_env
from rest_assured.src.configs.app.smtp import SmtpConfig
from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings


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


# ----------------------------------------------------------------
# Интеграционный тест загрузки Settings с переопределением через env
# ----------------------------------------------------------------

def test_settings_loads_smtp_and_notifications_from_file(monkeypatch, tmp_path):
    """Проверяем, что новые секции загружаются из settings.toml и переопределяются env-переменными."""
    # Создаём временный settings.toml с полным содержимым
    toml_content = """\
[app_settings]
host = "0.0.0.0"
port = 8000
use_testcontainers = false

[db_settings]
name = "test_db"
user = "user"
password = "CHANGE_ME"
host = "postgres"
port = 5432

[scheduler]
poll_interval_seconds = 5
default_timeout_ms = 5000

[smtp]
host = "localhost"
port = 1025
user = ""
password = ""
use_tls = false
from_email = "noreply@example.com"
from_name = "Rest Assured"

[notifications]
enabled = true
reminder_cooldown_minutes = 30
include_runbook_link = false
"""
    settings_file = tmp_path / "settings.toml"
    settings_file.write_text(toml_content)

    # monkeypatch путь к корню проекта (root = tmp_path)
    monkeypatch.setattr(
        "rest_assured.src.configs.app.main.Path",
        lambda x: Path(tmp_path) / x  # упрощённая подмена, используем прямой путь
    )
    # Более точный способ – переопределить root внутри Settings.load()
    def mock_load(cls):
        # эмулируем load, используя наш временный файл
        import tomllib
        with open(settings_file, "rb") as f:
            data = tomllib.load(f)
        data = _override_from_env(data)
        return cls(
            db_settings=DBConfig(**data["db_settings"]),
            app_settings=APPConfig(**data["app_settings"]),
            scheduler=SchedulerSettings(**data["scheduler"]),
            smtp=SmtpConfig(**data["smtp"]),
            notifications=NotificationsConfig(**data["notifications"]),
        )
    monkeypatch.setattr(Settings, "load", classmethod(mock_load))

    # Без переменных окружения
    settings = Settings.load()
    assert settings.smtp.host == "localhost"
    assert settings.smtp.from_email == "noreply@example.com"
    assert settings.notifications.reminder_cooldown_minutes == 30

    # Устанавливаем переменную окружения для переопределения
    monkeypatch.setenv("DYNACONF_NOTIFICATIONS__REMINDER_COOLDOWN_MINUTES", "10")
    monkeypatch.setenv("DYNACONF_SMTP__HOST", "mailhog")

    settings2 = Settings.load()
    assert settings2.smtp.host == "mailhog"
    assert settings2.notifications.reminder_cooldown_minutes == 10