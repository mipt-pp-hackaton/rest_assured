"""Планировщик проверок сервисов."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service
from rest_assured.src.scheduler.evaluator import evaluate_response

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """Менеджер асинхронных воркеров для проверки сервисов."""

    def __init__(self) -> None:
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._callbacks: list[Callable[[CheckResult], Awaitable[None]]] = []
        self._http_client: httpx.AsyncClient | None = None
        self._running = False
        self._checks_total = 0
        self._checks_failed = 0
        self._session_factory: Callable[[], AsyncSession] | None = None

    @property
    def active_workers_count(self) -> int:
        """Количество активных воркеров."""
        return len([w for w in self._workers.values() if not w.done()])

    @property
    def stats(self) -> dict:
        """Статистика планировщика."""
        return {
            "checks_total": self._checks_total,
            "checks_failed": self._checks_failed,
            "active_workers_count": self.active_workers_count,
        }

    def register_callback(
        self, fn: Callable[[CheckResult], Awaitable[None]]
    ) -> None:
        """Регистрирует callback для обработки результатов проверок."""
        self._callbacks.append(fn)
        logger.info("Registered callback: %s", fn.__name__)

    async def start(
        self,
        session_factory: Callable[[], AsyncSession],
    ) -> None:
        """Запускает раннер и HTTP-клиент, загружает сервисы из БД."""
        self._session_factory = session_factory
        self._http_client = httpx.AsyncClient(
            timeout=settings.scheduler.http_timeout_seconds,
        )
        self._running = True
        await self._load_services()
        logger.info("SchedulerRunner started")

    async def stop(self) -> None:
        """Останавливает все воркеры и закрывает HTTP-клиент."""
        self._running = False

        for task in self._workers.values():
            task.cancel()

        if self._workers:
            await asyncio.gather(*self._workers.values(), return_exceptions=True)
        self._workers.clear()

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info("SchedulerRunner stopped")

    async def _load_services(self) -> None:
        """Загружает активные сервисы из БД."""
        assert self._session_factory is not None
        session = self._session_factory()
        try:
            result = await session.execute(
                select(Service).where(Service.is_active == True)  # noqa: E712
            )
            services = result.scalars().all()

            for service in services:
                self.add_service(
                    service_id=str(service.id),
                    url=service.url,
                    interval_ms=service.interval_ms,
                )
        finally:
            await session.close()

    def add_service(self, service_id: str, url: str, interval_ms: int) -> None:
        """Добавляет воркер для сервиса."""
        if service_id in self._workers and not self._workers[service_id].done():
            self.reschedule(service_id, interval_ms)
            return

        task = asyncio.create_task(
            self._worker_loop(service_id, url, interval_ms)
        )
        self._workers[service_id] = task
        logger.info(
            "Added worker for service %s (interval=%dms)", service_id, interval_ms
        )

    def remove_service(self, service_id: str) -> None:
        """Удаляет воркер сервиса."""
        if service_id in self._workers:
            self._workers[service_id].cancel()
            del self._workers[service_id]
            logger.info("Removed worker for service %s", service_id)

    def reschedule(self, service_id: str, new_interval_ms: int) -> None:
        """Обновляет интервал проверки (отменяет старый воркер)."""
        if service_id in self._workers:
            self._workers[service_id].cancel()
            logger.info(
                "Rescheduled service %s to interval %dms",
                service_id,
                new_interval_ms,
            )

    async def reschedule_from_db(self, service_id: str) -> None:
        """Перечитывает сервис из БД и обновляет воркер."""
        assert self._session_factory is not None
        session = self._session_factory()
        try:
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalar_one_or_none()

            if service is None or not service.is_active:
                self.remove_service(service_id)
            else:
                self.add_service(
                    service_id=str(service.id),
                    url=service.url,
                    interval_ms=service.interval_ms,
                )
        finally:
            await session.close()

    async def _worker_loop(
        self, service_id: str, url: str, interval_ms: int
    ) -> None:
        """Цикл проверки одного сервиса."""
        while self._running:
            try:
                await self._check_service(service_id, url)
            except asyncio.CancelledError:
                logger.info("Worker for service %s cancelled", service_id)
                break
            except Exception:
                logger.exception("Error in worker for service %s", service_id)

            await asyncio.sleep(interval_ms / 1000.0)

    async def _check_service(self, service_id: str, url: str) -> None:
        """Выполняет одну проверку сервиса."""
        self._checks_total += 1
        started = asyncio.get_event_loop().time()

        status_code = None
        error_message = None

        try:
            response = await self._http_client.get(url)
            status_code = response.status_code
            response_time = (asyncio.get_event_loop().time() - started) * 1000
        except httpx.TimeoutException:
            error_message = "timeout"
            response_time = None
        except httpx.RequestError as exc:
            error_message = str(exc)
            response_time = None

        is_up = evaluate_response(status_code, error_message)
        if not is_up:
            self._checks_failed += 1

        check_result = CheckResult(
            service_id=service_id,
            is_up=is_up,
            response_time_ms=response_time,
            status_code=status_code,
            error_message=error_message,
        )

        await self._save_result(check_result)
        await self._fire_callbacks(check_result)

    async def _save_result(self, check_result: CheckResult) -> None:
        """Сохраняет результат проверки в БД."""
        assert self._session_factory is not None
        session = self._session_factory()
        try:
            session.add(check_result)
            await session.commit()
        except Exception:
            logger.exception("Failed to save check result")
        finally:
            await session.close()

    async def _fire_callbacks(self, check_result: CheckResult) -> None:
        """Вызывает зарегистрированные callback'и."""
        if self._callbacks:
            await asyncio.gather(
                *[cb(check_result) for cb in self._callbacks],
                return_exceptions=True,
            )


# Глобальный экземпляр
scheduler_runner = SchedulerRunner()
