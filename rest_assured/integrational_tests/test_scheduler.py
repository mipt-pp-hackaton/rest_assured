"""Интеграционные тесты для планировщика."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.fixture
def runner():
    """Создает экземпляр SchedulerRunner."""
    return SchedulerRunner()


@pytest.mark.asyncio
async def test_add_service_creates_worker(runner):
    """Добавление сервиса создает воркер."""
    runner._http_client = MagicMock(spec=httpx.AsyncClient)
    runner._http_client.get = AsyncMock()
    runner._running = True
    runner._db_session_factory = AsyncMock()

    runner.add_service("svc-1", "http://example.com", 5000)
    assert "svc-1" in runner._workers

    runner.remove_service("svc-1")


@pytest.mark.asyncio
async def test_remove_service_stops_worker(runner):
    """Удаление сервиса останавливает воркер."""
    runner._http_client = MagicMock(spec=httpx.AsyncClient)
    runner._http_client.get = AsyncMock()
    runner._running = True
    runner._db_session_factory = AsyncMock()

    runner.add_service("svc-2", "http://example.com", 5000)
    runner.remove_service("svc-2")
    assert "svc-2" not in runner._workers


@pytest.mark.asyncio
async def test_reschedule_cancels_old_task():
    """Изменение интервала отменяет старую задачу."""
    runner = SchedulerRunner()
    runner._http_client = MagicMock(spec=httpx.AsyncClient)
    runner._http_client.get = AsyncMock()
    runner._running = True
    runner._db_session_factory = AsyncMock()

    runner.add_service("svc-3", "http://example.com", 5000)
    old_task = runner._workers["svc-3"]

    runner.reschedule("svc-3", 10000)
    await asyncio.sleep(0)  # даем事件ому циклу обработать отмену
    assert old_task.cancelled() or old_task.done()

    runner.remove_service("svc-3")


@pytest.mark.asyncio
async def test_health_stats(runner):
    """Проверяет счетчики health-check."""
    runner._http_client = MagicMock(spec=httpx.AsyncClient)
    runner._checks_total = 10
    runner._checks_failed = 2
    runner._running = True
    runner._db_session_factory = AsyncMock()

    runner.add_service("svc-4", "http://example.com", 5000)

    stats = runner.stats
    assert stats["checks_total"] == 10
    assert stats["checks_failed"] == 2
    assert stats["active_workers_count"] >= 1

    runner.remove_service("svc-4")


@pytest.mark.asyncio
async def test_callback_registration(runner):
    """Проверяет регистрацию callback."""
    async def dummy_callback(result: CheckResult) -> None:
        pass

    runner.register_callback(dummy_callback)
    assert len(runner._callbacks) == 1
    assert runner._callbacks[0] == dummy_callback


@pytest.mark.asyncio
async def test_graceful_shutdown(runner):
    """Проверяет корректное завершение."""
    runner._http_client = MagicMock(spec=httpx.AsyncClient)
    runner._http_client.aclose = AsyncMock()
    runner._running = True
    runner._db_session_factory = AsyncMock()

    runner.add_service("svc-5", "http://example.com", 5000)
    
    client = runner._http_client
    await runner.stop()

    assert not runner._workers
    assert runner._http_client is None
    client.aclose.assert_awaited_once()
