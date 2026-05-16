"""Тесты для SchedulerRunner (T2.4)."""

import pytest

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.scheduler.runner import SchedulerRunner


def test_register_callback():
    r = SchedulerRunner()

    async def cb(check):
        pass

    r.register_callback(cb)
    assert len(r._callbacks) == 1
    assert r._callbacks[0] == cb


@pytest.mark.asyncio
async def test_fire_callbacks_swallows_errors():
    r = SchedulerRunner()

    good_called = False
    bad_called = False

    async def good(check):
        nonlocal good_called
        good_called = True

    async def bad(check):
        nonlocal bad_called
        bad_called = True
        raise RuntimeError("callback error")

    r.register_callback(good)
    r.register_callback(bad)

    fake_check = CheckResult(
        service_id=1,
        is_up=True,
        http_status=200,
        latency_ms=42,
    )
    await r.fire_callbacks(fake_check)

    assert good_called, "Good callback should have been called"
    assert bad_called, "Bad callback should have been called (before raising)"


def test_active_workers_count():
    r = SchedulerRunner()
    assert r.active_workers_count == 0


def test_stats():
    r = SchedulerRunner()
    r.checks_total = 10
    r.checks_failed = 3
    assert r.stats["checks_total"] == 10
    assert r.stats["checks_failed"] == 3
    assert r.stats["active_workers_count"] == 0
