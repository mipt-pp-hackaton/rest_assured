"""Слушатель уведомлений PostgreSQL для динамического обновления."""

import asyncio
import logging

import asyncpg

from rest_assured.src.configs.app.main import settings

logger = logging.getLogger(__name__)


class ServiceChangeListener:
    """Слушает канал service_changed через PostgreSQL LISTEN/NOTIFY."""

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._running = False
        self._runner = None

    def set_runner(self, runner) -> None:
        """Привязывает SchedulerRunner для обновлений."""
        self._runner = runner

    async def start(self) -> None:
        """Подключается к PostgreSQL и начинает слушать."""
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
            logger.info("ServiceChangeListener started")
        except Exception:
            logger.warning("Could not start ServiceChangeListener (DB not available)")

    async def stop(self) -> None:
        """Закрывает соединение."""
        self._running = False
        if self._conn:
            await self._conn.close()
            self._conn = None
        logger.info("ServiceChangeListener stopped")

    async def _on_service_changed(self, conn, pid, channel, payload) -> None:
        """Обрабатывает уведомление об изменении сервиса."""
        logger.info("Received notification: %s = %s", channel, payload)
        if self._runner and payload:
            service_id = payload
            await self._runner.reschedule_from_db(service_id)
