"""Тесты конфигурации планировщика (T2.1)."""

from rest_assured.src.configs.app.main import settings


def test_scheduler_config_defaults():
    """Проверяет значения по умолчанию для конфигурации планировщика."""
    assert settings.scheduler.poll_interval_seconds == 5, (
        f"Expected poll_interval_seconds=5, " f"got {settings.scheduler.poll_interval_seconds}"
    )
    assert settings.scheduler.default_timeout_ms == 5000, (
        f"Expected default_timeout_ms=5000, " f"got {settings.scheduler.default_timeout_ms}"
    )


def test_scheduler_config_types():
    """Проверяет типы полей конфигурации."""
    assert isinstance(settings.scheduler.poll_interval_seconds, int)
    assert isinstance(settings.scheduler.default_timeout_ms, int)


def test_scheduler_config_positive():
    """Проверяет, что значения положительные."""
    assert settings.scheduler.poll_interval_seconds > 0
    assert settings.scheduler.default_timeout_ms > 0
