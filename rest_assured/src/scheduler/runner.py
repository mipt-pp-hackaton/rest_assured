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

    async def start(self) -> None:
        """Поднять воркеры на все is_active=True сервисы (вызывается из lifespan.startup)."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.scheduler.default_timeout_ms / 1000),
        )
        session = get_session()
        try:
            services = (await session.exec(select(Service).where(Service.is_active == True))).all()
        finally:
            await session.close()

        for s in services:
            self._spawn(s)
        logger.info("scheduler started: {} workers", len(self._tasks))

    def _spawn(self, service: Service) -> None:
        if service.id in self._tasks:
            return
        # Отложенный импорт worker_loop (T2.5)
        from rest_assured.src.scheduler.worker import worker_loop

        task = asyncio.create_task(
            worker_loop(self, service),
            name=f"check_worker_{service.id}",
        )
        self._tasks[service.id] = task
        logger.info("Spawned worker for service %s (id=%s)", service.name, service.id)

    async def reschedule(self, service_id: int) -> None:
        """Пересобрать таску при изменении сервиса (T2.8)."""
        if service_id not in self._tasks:
            logger.warning("No task found for service %s to reschedule", service_id)
            return

        task = self._tasks[service_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._tasks.pop(service_id, None)

        # Перечитать сервис из БД и запустить заново
        session = get_session()
        try:
            service = await session.get(Service, service_id)
            if service and service.is_active:
                self._spawn(service)
            else:
                logger.info(
                    "Service %s is no longer active, worker not restarted",
                    service_id,
                )
        finally:
            await session.close()

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
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("scheduler stopped")

    @property
    def http_client(self) -> httpx.AsyncClient:
        assert self._client is not None, "SchedulerRunner not started"
        return self._client


# Глобальный singleton
scheduler_runner = SchedulerRunner()
