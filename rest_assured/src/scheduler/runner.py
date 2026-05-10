"""Планировщик проверок сервисов (T2.4)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

import httpx
from sqlmodel import select

from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.scheduler.worker import worker_loop

logger = logging.getLogger(__name__)

CheckCallback = Callable[[CheckResult], Awaitable[None]]


class SchedulerRunner:
    """Корневой объект планировщика (T2.4)."""

    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._callbacks: list[CheckCallback] = []
        self._client: httpx.AsyncClient | None = None
        self.checks_total = 0
        self.checks_failed = 0
        self.last_loop_at: datetime | None = None

    def register_callback(self, fn: CheckCallback) -> None:
        """Эпик 4 регистрирует здесь handle_check_result."""
        self._callbacks.append(fn)
        logger.info("Registered callback: %s", fn.__name__)

    @property
    def active_workers_count(self) -> int:
        return len(self._tasks)

    @property
    def stats(self) -> dict:
        """Статистика для GET /api/health/scheduler."""
        return {
            "checks_total": self.checks_total,
            "checks_failed": self.checks_failed,
            "active_workers_count": self.active_workers_count,
        }

    def active_service_ids(self) -> set[int]:
        """Снимок текущих обслуживаемых service.id (для listener'а)."""
        return set(self._tasks)

    async def start(self) -> None:
        """Поднять воркеры на все is_active=True сервисы (вызывается из lifespan.startup).

        При недоступной БД делается 3 попытки с интервалом 1 секунда; после неуспеха
        стартуем без воркеров (listener восстановит при первом poll'е).
        """
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.scheduler.default_timeout_ms / 1000),
            follow_redirects=False,
        )

        services: list[Service] = []
        for attempt in range(3):
            try:
                session = get_session()
                try:
                    services = (
                        await session.exec(select(Service).where(Service.is_active.is_(True)))
                    ).all()
                finally:
                    await session.close()
                break
            except Exception as e:
                if attempt < 2:
                    logger.warning(
                        "DB not ready (attempt %s/3): %r — retrying in 1s",
                        attempt + 1,
                        e,
                    )
                    await asyncio.sleep(1)
                else:
                    logger.warning(
                        "DB unreachable after 3 attempts; starting with empty workers, "
                        "listener will recover",
                        exc_info=True,
                    )
                    services = []

        for s in services:
            self._spawn(s)
        logger.info("scheduler started: %s workers", len(self._tasks))

    def _spawn(self, service: Service) -> None:
        if service.id is None or service.id in self._tasks:
            return
        task = asyncio.create_task(
            worker_loop(self, service),
            name=f"check_worker_{service.id}",
        )
        self._tasks[service.id] = task
        logger.info("Spawned worker for service %s (id=%s)", service.name, service.id)

    def ensure_running(self, service: Service) -> None:
        """Идемпотентный wrapper над `_spawn`."""
        if service.id is None or service.id in self._tasks:
            return
        self._spawn(service)

    async def stop_service(self, service_id: int) -> None:
        """Отменяет задачу одного сервиса, ждёт её завершения и удаляет ключ."""
        task = self._tasks.pop(service_id, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    async def refresh_service(self, service_id: int) -> None:
        """Перезапуск воркера по service_id: stop + reread + ensure_running."""
        await self.stop_service(service_id)
        session = get_session()
        try:
            service = await session.get(Service, service_id)
        finally:
            await session.close()
        if service is not None and service.is_active:
            self.ensure_running(service)

    # Alias для обратной совместимости (listener.py использует имя reschedule).
    reschedule = refresh_service

    async def fire_callbacks(self, check: CheckResult) -> None:
        """Вызвать все коллбэки с protection от падений."""
        if not self._callbacks:
            return
        await asyncio.gather(
            *(cb(check) for cb in self._callbacks),
            return_exceptions=True,
        )

    async def stop(self) -> None:
        """Graceful shutdown (T2.9)."""
        logger.info("Stopping scheduler runner...")
        for task in list(self._tasks.values()):
            task.cancel()
        if self._tasks:
            results = await asyncio.gather(*self._tasks.values(), return_exceptions=True)
            for r in results:
                if isinstance(r, BaseException) and not isinstance(r, asyncio.CancelledError):
                    logger.error("worker raised: %r", r, exc_info=r)
        self._tasks.clear()

        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("scheduler stopped")

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("SchedulerRunner not started")
        return self._client
