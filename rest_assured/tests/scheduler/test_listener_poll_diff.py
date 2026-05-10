"""T16: poll-loop использует публичные active_service_ids/ensure_running/stop_service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner
from rest_assured.src.models.services import Service


@pytest.mark.asyncio
async def test_poll_starts_new_services_and_stops_removed(monkeypatch):
    # mock socket so Service URL validation passes
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
        ],
    )

    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.active_service_ids = MagicMock(return_value={1})
    mock_runner.ensure_running = MagicMock()
    mock_runner.stop_service = AsyncMock()
    listener.set_runner(mock_runner)

    # БД возвращает только Service id=2 (активный)
    s2 = Service(
        id=2,
        name="x",
        url="http://example.com",
        interval_ms=1000,
        is_active=True,
    )
    fake_session = MagicMock()
    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[s2])
    fake_session.exec = AsyncMock(return_value=exec_result)
    fake_session.close = AsyncMock()
    monkeypatch.setattr(
        "rest_assured.src.scheduler.listener.get_session",
        lambda: fake_session,
    )

    await listener._poll_once()

    mock_runner.ensure_running.assert_called_once_with(s2)
    mock_runner.stop_service.assert_awaited_once_with(1)
