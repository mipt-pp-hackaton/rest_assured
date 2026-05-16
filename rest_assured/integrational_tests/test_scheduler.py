"""Интеграционные тесты планировщика (обновленные)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.fixture
def runner():
    return SchedulerRunner()


@pytest.mark.asyncio
async def test_callback_registration(runner):
    """Проверяет регистрацию callback'ов."""

    async def dummy_callback(result: CheckResult) -> None:
        pass

    runner.register_callback(dummy_callback)
    assert len(runner._callbacks) == 1
    assert runner._callbacks[0] == dummy_callback


@pytest.mark.asyncio
async def test_fire_callbacks_swallows_errors(runner):
    """Проверяет, что ошибка в callback не валит остальные."""
    good_called = False
    bad_called = False

    async def good_callback(check: CheckResult):
        nonlocal good_called
        good_called = True

    async def bad_callback(check: CheckResult):
        nonlocal bad_called
        bad_called = True
        raise RuntimeError("test error")

    runner.register_callback(good_callback)
    runner.register_callback(bad_callback)

    check = CheckResult(service_id=1, is_up=True, http_status=200, latency_ms=42)
    await runner.fire_callbacks(check)

    assert good_called
    assert bad_called


@pytest.mark.asyncio
async def test_graceful_shutdown(runner):
    """Проверяет остановку с закрытием HTTP-клиента."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.aclose = AsyncMock()
    runner._client = mock_client

    await runner.stop()

    mock_client.aclose.assert_awaited_once()
    assert runner._client is None
    assert not runner._tasks


def test_stats(runner):
    """Проверяет формирование статистики."""
    runner.checks_total = 42
    runner.checks_failed = 7

    stats = runner.stats
    assert stats["checks_total"] == 42
    assert stats["checks_failed"] == 7
    assert stats["active_workers_count"] == 0
