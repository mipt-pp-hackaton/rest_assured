"""T16: невалидный payload (нечисло, None, мусор) не приводит к падению."""

import logging

import pytest
from unittest.mock import AsyncMock, MagicMock

from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_none_payload_does_not_call_runner():
    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.refresh_service = AsyncMock()
    listener.set_runner(mock_runner)

    await listener.on_service_changed(None, 0, "service_changed", None)
    mock_runner.refresh_service.assert_not_called()


@pytest.mark.asyncio
async def test_empty_payload_does_not_call_runner():
    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.refresh_service = AsyncMock()
    listener.set_runner(mock_runner)

    await listener.on_service_changed(None, 0, "service_changed", "")
    mock_runner.refresh_service.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_int_payload_is_sanitized_in_logs(caplog):
    listener = ServiceChangeListener()
    mock_runner = MagicMock(spec=SchedulerRunner)
    mock_runner.refresh_service = AsyncMock()
    listener.set_runner(mock_runner)

    with caplog.at_level(logging.INFO, logger="rest_assured.src.scheduler.listener"):
        await listener.on_service_changed(None, 0, "service_changed", "1\nFAKE: hacked")

    # В логах не должно быть голого \n из payload — должен быть экранирован.
    combined = "\n".join(rec.getMessage() for rec in caplog.records)
    # Само сообщение лога может содержать \n как разделитель строк лога, но
    # внутри payload (после ключевых слов) перевод строки экранирован.
    assert "1\\nFAKE: hacked" in combined
    mock_runner.refresh_service.assert_not_called()
