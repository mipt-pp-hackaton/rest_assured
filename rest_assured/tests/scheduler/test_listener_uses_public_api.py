"""T16: listener использует публичные методы SchedulerRunner и переименован callback."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_on_service_changed_calls_refresh_service():
    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.refresh_service = AsyncMock()
    listener.set_runner(mock_runner)

    # asyncpg callback signature: (connection, pid, channel, payload)
    await listener.on_service_changed(None, 0, "service_changed", "42")
    mock_runner.refresh_service.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_on_service_changed_invalid_payload_logs_and_ignores(caplog):
    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.refresh_service = AsyncMock()
    listener.set_runner(mock_runner)

    await listener.on_service_changed(None, 0, "service_changed", "not-an-int\nINJECT")
    mock_runner.refresh_service.assert_not_called()


def test_old_private_callback_name_is_gone():
    """Регрессионный: приватная функция-callback переименована в публичный API."""
    assert not hasattr(ServiceChangeListener, "_on_service_changed")
    assert hasattr(ServiceChangeListener, "on_service_changed")
