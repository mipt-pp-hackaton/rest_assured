"""T15: счётчики обновляются ДО session.commit() (даже если commit падает)."""

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from rest_assured.src.models.services import Service
from rest_assured.src.scheduler.runner import SchedulerRunner
from rest_assured.src.scheduler.worker import worker_loop


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))],
    )


@pytest.mark.asyncio
async def test_counters_incremented_even_when_commit_fails(monkeypatch):
    runner = SchedulerRunner()
    runner._client = httpx.AsyncClient()  # type: ignore[attr-defined]
    service = Service(id=1, name="x", url="http://example.com", interval_ms=1000)

    # mock http call -> 200
    async def _fake_request(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", "http://example.com"))

    monkeypatch.setattr(runner._client, "request", _fake_request)

    # mock get_session to return a session whose commit raises
    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock(side_effect=Exception("DB down"))
    fake_session.rollback = AsyncMock()
    fake_session.close = AsyncMock()
    monkeypatch.setattr(
        "rest_assured.src.scheduler.worker.get_session",
        lambda: fake_session,
    )

    # patch sleep so iteration kicks off quickly
    original_sleep = asyncio.sleep

    async def fast_sleep(delay):
        await original_sleep(min(delay, 0.01))

    monkeypatch.setattr("rest_assured.src.scheduler.worker.asyncio.sleep", fast_sleep)

    task = asyncio.create_task(worker_loop(runner, service))
    await original_sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        await runner._client.aclose()

    # at least one check counted even though commit failed
    assert runner.checks_total >= 1, "checks_total must grow even when commit fails"
    # response was 200, expected_status is None -> is_up=True -> failed not incremented
    assert runner.last_loop_at is not None


@pytest.mark.asyncio
async def test_counters_failed_increments_on_5xx(monkeypatch):
    runner = SchedulerRunner()
    runner._client = httpx.AsyncClient()
    service = Service(id=1, name="x", url="http://example.com", interval_ms=1000)

    async def _fake_request(*args, **kwargs):
        return httpx.Response(500, request=httpx.Request("GET", "http://example.com"))

    monkeypatch.setattr(runner._client, "request", _fake_request)

    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()
    fake_session.close = AsyncMock()
    monkeypatch.setattr(
        "rest_assured.src.scheduler.worker.get_session",
        lambda: fake_session,
    )

    original_sleep = asyncio.sleep

    async def fast_sleep(delay):
        await original_sleep(min(delay, 0.01))

    monkeypatch.setattr("rest_assured.src.scheduler.worker.asyncio.sleep", fast_sleep)

    task = asyncio.create_task(worker_loop(runner, service))
    await original_sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        await runner._client.aclose()

    assert runner.checks_total >= 1
    assert runner.checks_failed >= 1
