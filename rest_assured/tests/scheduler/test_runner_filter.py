"""T14: Проверяет, что start() запускает воркер только для is_active=True (BUG fix)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import rest_assured.src.scheduler.runner as runner_mod
from rest_assured.src.scheduler.runner import SchedulerRunner


class _FakeService:
    """Lightweight stand-in для Service (минует SSRF-валидацию URL)."""

    def __init__(self, id: int, is_active: bool, name: str = "svc") -> None:
        self.id = id
        self.is_active = is_active
        self.name = name
        self.url = "https://example.test/"
        self.http_method = "GET"
        self.interval_ms = 60_000
        self.expected_status = None


@pytest.mark.asyncio
async def test_start_spawns_only_active_services(monkeypatch):
    """С двумя сервисами (active=True/False) воркер запускается только для активного."""
    active = _FakeService(id=1, is_active=True, name="active_one")
    inactive = _FakeService(id=2, is_active=False, name="inactive_one")

    fake_session = MagicMock()
    fake_session.close = AsyncMock()
    exec_result = MagicMock()
    # имитируем фильтр на стороне БД: возвращаем только активные
    exec_result.all = MagicMock(return_value=[active])
    fake_session.exec = AsyncMock(return_value=exec_result)

    def fake_get_session():
        return fake_session

    monkeypatch.setattr(runner_mod, "get_session", fake_get_session)

    spawned: list[int] = []

    async def fake_worker_loop(runner_self, service):
        spawned.append(service.id)
        # держим задачу живой, пока её не отменят
        try:
            while True:
                import asyncio

                await asyncio.sleep(3600)
        except Exception:
            raise

    monkeypatch.setattr(runner_mod, "worker_loop", fake_worker_loop)

    runner = SchedulerRunner()
    try:
        await runner.start()

        assert active.id in runner._tasks
        assert inactive.id not in runner._tasks
        assert runner.active_workers_count == 1
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_start_uses_is_method_not_python_is(monkeypatch):
    """Регрессионный: убеждаемся, что в SELECT идёт column.is_(True), а не Python `is True`."""
    captured: dict = {}

    fake_session = MagicMock()
    fake_session.close = AsyncMock()
    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[])

    async def _exec_capture(stmt):
        captured["stmt"] = stmt
        return exec_result

    fake_session.exec = AsyncMock(side_effect=_exec_capture)

    def fake_get_session():
        return fake_session

    monkeypatch.setattr(runner_mod, "get_session", fake_get_session)

    async def fake_worker_loop(runner_self, service):
        pass

    monkeypatch.setattr(runner_mod, "worker_loop", fake_worker_loop)

    runner = SchedulerRunner()
    try:
        await runner.start()
    finally:
        await runner.stop()

    # Сгенерированный SQL должен фильтровать по is_active = TRUE, а не быть тривиально false.
    sql_text = str(captured["stmt"]).lower()
    assert "is_active" in sql_text
    # Триггер обнаружения бага: фильтр сравнения через Python `is` даёт "WHERE false".
    assert "where false" not in sql_text
