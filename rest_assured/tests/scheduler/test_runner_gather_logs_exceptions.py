"""T14: stop() логирует исключения из воркеров через gather(..., return_exceptions=True)."""

import asyncio

import pytest

from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_stop_logs_worker_exceptions(caplog):
    """Если воркер кидает RuntimeError, stop() не падает и логирует 'worker raised'."""
    runner = SchedulerRunner()

    async def boom():
        raise RuntimeError("boom!")

    task = asyncio.create_task(boom(), name="check_worker_99")
    runner._tasks[99] = task
    # Дать задаче выполниться (и сразу упасть с RuntimeError) до вызова stop().
    # Если бы stop() сразу её cancel'нул, мы бы получили CancelledError вместо
    # RuntimeError — проверка перестала бы покрывать целевой сценарий.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert task.done() and task.exception() is not None

    caplog.set_level("ERROR", logger="rest_assured.src.scheduler.runner")
    await runner.stop()

    errors = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
    assert any(
        "worker raised" in m for m in errors
    ), f"expected 'worker raised' in logs, got: {errors}"


@pytest.mark.asyncio
async def test_stop_does_not_log_cancellation_as_error(caplog):
    """Отмена воркера — это нормально; CancelledError не должно логироваться."""
    runner = SchedulerRunner()

    async def slow():
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(slow(), name="check_worker_5")
    # Дать таске начать выполняться
    await asyncio.sleep(0)
    runner._tasks[5] = task

    caplog.set_level("ERROR", logger="rest_assured.src.scheduler.runner")
    await runner.stop()

    cancellation_errors = [
        r.getMessage()
        for r in caplog.records
        if r.levelname == "ERROR" and "worker raised" in r.getMessage()
    ]
    assert cancellation_errors == []


@pytest.mark.asyncio
async def test_stop_clears_tasks_even_on_failures():
    runner = SchedulerRunner()

    async def boom():
        raise RuntimeError("x")

    async def slow():
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    runner._tasks[1] = asyncio.create_task(boom())
    runner._tasks[2] = asyncio.create_task(slow())

    await runner.stop()

    assert runner._tasks == {}
