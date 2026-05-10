"""Слушатель уведомлений PostgreSQL для динамического обновления (T2.7)."""

import asyncio
import logging

import asyncpg
from sqlmodel import select

from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.services import Service
from rest_assured.src.repositories.database_session import get_session

logger = logging.getLogger(__name__)


class ServiceChangeListener:
    """Слушает канал service_changed через PostgreSQL LISTEN/NOTIFY."""

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._running = False
        self._runner = None
        self._poll_task: asyncio.Task[None] | None = None

    def set_runner(self, runner) -> None:
        """Привязывает SchedulerRunner для обновлений."""
        self._runner = runner

    async def start(self) -> None:
        """Подключается к PostgreSQL, начинает LISTEN и fallback poll."""
        try:
            self._conn = await asyncpg.connect(
                host=settings.db_settings.host,
                port=settings.db_settings.port,
                user=settings.db_settings.user,
                password=settings.db_settings.password,
                database=settings.db_settings.name,
            )
            await self._conn.add_listener("service_changed", self._on_service_changed)
            self._running = True
            logger.info("ServiceChangeListener started (LISTEN)")
        except Exception:
            logger.warning("Could not start LISTEN, falling back to poll-only mode")

        # Всегда запускаем fallback poll
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Закрывает соединение и останавливает poll."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._conn:
            await self._conn.close()
            self._conn = None
        logger.info("ServiceChangeListener stopped")

    async def _on_service_changed(self, conn, pid, channel, payload) -> None:
        """Обрабатывает уведомление об изменении сервиса."""
        logger.info("Received notification: channel=%s, payload=%s", channel, payload)
        if self._runner and payload:
            try:
                service_id = int(payload)
                await self._runner.reschedule(service_id)
            except (ValueError, TypeError):
                logger.error("Invalid payload for service_changed: %s", payload)

    async def _poll_loop(self) -> None:
        """Fallback-poll: раз в N секунд проверяет изменения в БД."""
        poll_interval = settings.scheduler.poll_interval_seconds

        logger.info("Starting fallback poll loop (interval=%ds)", poll_interval)
        while self._running:
            try:
                await asyncio.sleep(poll_interval)
                if not self._running:
                    break

                session = get_session()
                try:
                    services = (
                        await session.exec(select(Service).where(Service.is_active == True))
                    ).all()
                finally:
                    await session.close()

                if self._runner:
                    active_ids = {s.id for s in services}
                    current_ids = set(self._runner._tasks.keys())

                    for sid in active_ids - current_ids:
                        logger.info("Poll: new service detected: %s", sid)
                        # Перечитываем сервис целиком
                        s = next((x for x in services if x.id == sid), None)
                        if s:
                            self._runner._spawn(s)

                    for sid in current_ids - active_ids:
                        logger.info("Poll: service deactivated: %s", sid)
                        await self._runner.reschedule(sid)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Poll iteration error: %s", e)
