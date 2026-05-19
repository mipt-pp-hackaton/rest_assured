"""Слушатель уведомлений PostgreSQL для динамического обновления (T2.7)."""

import asyncio
import logging

import asyncpg
from sqlmodel import select

from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.services import Service
from rest_assured.src.repositories.database_session import get_session

logger = logging.getLogger(__name__)


def _sanitize_log(s: str, limit: int = 200) -> str:
    """Экранирует управляющие символы и обрезает строку — защита от log-injection.

    Атакующий может вставить в `payload` `\\n` или `\\r`, чтобы подделать строку
    лога; `encode("unicode_escape")` превращает их в литералы.
    """
    if s is None:
        return ""
    cleaned = s[:limit].encode("unicode_escape").decode("ascii", errors="replace")
    return cleaned


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
                password=settings.db_settings.password.get_secret_value(),
                database=settings.db_settings.name,
            )
            await self._conn.add_listener("service_changed", self.on_service_changed)
            self._running = True
            logger.info("ServiceChangeListener started (LISTEN)")
        except Exception:
            logger.warning(
                "Could not start LISTEN, falling back to poll-only mode",
                exc_info=True,
            )
            # Если соединение было частично инициализировано — закрываем его.
            if self._conn is not None:
                try:
                    await self._conn.close()
                except Exception:
                    logger.debug("Error while closing half-open asyncpg connection", exc_info=True)
                self._conn = None
            self._running = True

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

    async def on_service_changed(self, conn, pid, channel, payload) -> None:
        """Обрабатывает уведомление об изменении сервиса.

        Зарегистрирован как внешний asyncpg callback, поэтому имя — публичное.
        """
        safe_channel = _sanitize_log(channel) if isinstance(channel, str) else channel
        safe_payload = _sanitize_log(payload) if isinstance(payload, str) else payload
        logger.info(
            "Received notification: channel=%s, payload=%s",
            safe_channel,
            safe_payload,
        )
        if self._runner and payload:
            try:
                service_id = int(payload)
            except (ValueError, TypeError):
                logger.error("Invalid payload for service_changed: %s", safe_payload)
                return
            await self._runner.refresh_service(service_id)

    async def _poll_once(self) -> None:
        """Одна итерация poll-loop'а — выделена для тестируемости."""
        session = get_session()
        try:
            services = (
                await session.exec(select(Service).where(Service.is_active.is_(True)))
            ).all()
        finally:
            await session.close()

        if not self._runner:
            return

        active_ids = {s.id for s in services if s.id is not None}
        current_ids = self._runner.active_service_ids()

        for sid in active_ids - current_ids:
            logger.info("Poll: new service detected: %s", sid)
            s = next((x for x in services if x.id == sid), None)
            if s:
                self._runner.ensure_running(s)

        for sid in current_ids - active_ids:
            logger.info("Poll: service deactivated: %s", sid)
            await self._runner.stop_service(sid)

    async def _poll_loop(self) -> None:
        """Fallback-poll: раз в N секунд проверяет изменения в БД."""
        poll_interval = settings.scheduler.poll_interval_seconds

        logger.info("Starting fallback poll loop (interval=%ds)", poll_interval)
        while self._running:
            try:
                await asyncio.sleep(poll_interval)
                if not self._running:
                    break
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Poll iteration error: %s", _sanitize_log(repr(e)))
