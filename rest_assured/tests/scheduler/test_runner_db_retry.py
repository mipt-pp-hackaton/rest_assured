"""T14: start() устойчив к недоступной БД — 3×1с retry, после неуспеха — warning + пустые воркеры."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import OperationalError

import rest_assured.src.scheduler.runner as runner_mod
from rest_assured.src.scheduler.runner import SchedulerRunner


@pytest.mark.asyncio
async def test_start_retries_db_and_succeeds_on_third_attempt(monkeypatch, caplog):
    """Первые 2 попытки кидают OperationalError, 3-я возвращает реальную сессию-мок."""
    attempts = {"n": 0}
    success_session = MagicMock()
    success_session.close = AsyncMock()
    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[])
    success_session.exec = AsyncMock(return_value=exec_result)

    def fake_get_session():
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise OperationalError("SELECT 1", {}, Exception("connect failed"))
        return success_session

    monkeypatch.setattr(runner_mod, "get_session", fake_get_session)

    # Ускорим тест: подменим asyncio.sleep на noop в модуле runner.
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(runner_mod.asyncio, "sleep", fast_sleep)

    runner = SchedulerRunner()
    caplog.set_level("WARNING", logger="rest_assured.src.scheduler.runner")
    try:
        await runner.start()
    finally:
        await runner.stop()

    assert attempts["n"] == 3
    # обе ранние попытки должны быть залогированы
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("attempt 1/3" in m for m in warnings)
    assert any("attempt 2/3" in m for m in warnings)


@pytest.mark.asyncio
async def test_start_does_not_raise_when_db_unreachable(monkeypatch, caplog):
    """После 3 неуспешных попыток start() не падает, а лишь логирует warning."""

    def failing_get_session():
        raise OperationalError("SELECT 1", {}, Exception("connect failed"))

    monkeypatch.setattr(runner_mod, "get_session", failing_get_session)

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(runner_mod.asyncio, "sleep", fast_sleep)

    runner = SchedulerRunner()
    caplog.set_level("WARNING", logger="rest_assured.src.scheduler.runner")
    try:
        await runner.start()  # не должно бросать
    finally:
        await runner.stop()

    assert runner._tasks == {}
    # Должно быть хотя бы одно сообщение об окончательной неудаче.
    final_warns = [
        r.getMessage()
        for r in caplog.records
        if r.levelname == "WARNING" and "DB unreachable" in r.getMessage()
    ]
    assert final_warns, "expected final 'DB unreachable' warning"
