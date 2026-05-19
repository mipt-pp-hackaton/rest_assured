"""T14: SSRF mitigation — httpx-клиент создаётся с follow_redirects=False."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

import rest_assured.src.services.scheduler.runner as runner_mod
from rest_assured.src.services.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_http_client_does_not_follow_redirects(monkeypatch):
    fake_session = MagicMock()
    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[])
    fake_session.exec = AsyncMock(return_value=exec_result)

    @asynccontextmanager
    async def fake_session_scope():
        yield fake_session

    monkeypatch.setattr(runner_mod, "session_scope", fake_session_scope)

    runner = SchedulerRunner()
    try:
        await runner.start()
        assert runner._client is not None
        # httpx.AsyncClient.follow_redirects сохраняется как атрибут.
        assert runner._client.follow_redirects is False
    finally:
        await runner.stop()
