"""T14: Public API для listener'а — active_service_ids, ensure_running, stop_service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import rest_assured.src.scheduler.runner as runner_mod
from rest_assured.src.scheduler.runner import SchedulerRunner


class _FakeService:
    def __init__(self, id: int, is_active: bool = True, name: str = "svc") -> None:
        self.id = id
        self.is_active = is_active
        self.name = name
        self.url = "https://example.test/"
        self.http_method = "GET"
        self.interval_ms = 60_000
        self.expected_status = None


@pytest.fixture
def fake_worker(monkeypatch):
    """worker_loop, который просто живёт до отмены."""

    async def fake_worker_loop(runner_self, service):
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr(runner_mod, "worker_loop", fake_worker_loop)
    return fake_worker_loop


@pytest.mark.asyncio
async def test_active_service_ids_returns_snapshot(fake_worker):
    runner = SchedulerRunner()
    s1 = _FakeService(id=1)
    s2 = _FakeService(id=2)

    runner._spawn(s1)
    runner._spawn(s2)

    ids = runner.active_service_ids()
    assert ids == {1, 2}
    assert isinstance(ids, set)

    # Должно быть копией — изменения в _tasks не отражаются на ранее полученном set.
    snapshot = runner.active_service_ids()
    popped = runner._tasks.pop(1, None)
    if popped is not None:
        popped.cancel()
        try:
            await popped
        except (asyncio.CancelledError, Exception):
            pass
    assert snapshot == {1, 2}

    # Cleanup
    await runner.stop()


@pytest.mark.asyncio
async def test_ensure_running_is_idempotent(fake_worker):
    runner = SchedulerRunner()
    s = _FakeService(id=42)

    runner.ensure_running(s)
    first_task = runner._tasks[42]

    runner.ensure_running(s)
    second_task = runner._tasks[42]

    assert first_task is second_task
    assert len(runner._tasks) == 1

    await runner.stop()


@pytest.mark.asyncio
async def test_ensure_running_skips_service_without_id(fake_worker):
    runner = SchedulerRunner()
    s = _FakeService(id=None)  # type: ignore[arg-type]

    runner.ensure_running(s)
    assert runner._tasks == {}


@pytest.mark.asyncio
async def test_stop_service_cancels_and_removes(fake_worker):
    runner = SchedulerRunner()
    s = _FakeService(id=7)
    runner.ensure_running(s)
    assert 7 in runner._tasks
    task = runner._tasks[7]

    await runner.stop_service(7)

    assert 7 not in runner._tasks
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_stop_service_unknown_id_is_noop(fake_worker):
    runner = SchedulerRunner()
    # не падает
    await runner.stop_service(999)
    assert runner._tasks == {}


@pytest.mark.asyncio
async def test_refresh_service_restarts_when_active(monkeypatch, fake_worker):
    runner = SchedulerRunner()
    s_old = _FakeService(id=5, is_active=True, name="old")
    runner.ensure_running(s_old)
    old_task = runner._tasks[5]

    s_new = _FakeService(id=5, is_active=True, name="new")

    fake_session = MagicMock()
    fake_session.close = AsyncMock()
    fake_session.get = AsyncMock(return_value=s_new)
    monkeypatch.setattr(runner_mod, "get_session", lambda: fake_session)

    await runner.refresh_service(5)

    assert 5 in runner._tasks
    assert runner._tasks[5] is not old_task

    await runner.stop()


@pytest.mark.asyncio
async def test_refresh_service_drops_when_inactive(monkeypatch, fake_worker):
    runner = SchedulerRunner()
    s_old = _FakeService(id=11, is_active=True)
    runner.ensure_running(s_old)

    s_after = _FakeService(id=11, is_active=False)
    fake_session = MagicMock()
    fake_session.close = AsyncMock()
    fake_session.get = AsyncMock(return_value=s_after)
    monkeypatch.setattr(runner_mod, "get_session", lambda: fake_session)

    await runner.refresh_service(11)

    assert 11 not in runner._tasks


@pytest.mark.asyncio
async def test_reschedule_is_alias_of_refresh_service():
    """Listener.py использует имя reschedule — он должен остаться функциональным."""
    assert SchedulerRunner.reschedule is SchedulerRunner.refresh_service


def test_no_module_level_singleton():
    """Singleton `scheduler_runner = SchedulerRunner()` должен быть удалён."""
    assert not hasattr(runner_mod, "scheduler_runner")


def test_http_client_raises_runtime_error_when_not_started():
    runner = SchedulerRunner()
    with pytest.raises(RuntimeError, match="not started"):
        _ = runner.http_client
