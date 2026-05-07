"""Воркер сервиса: цикл sleep → request → evaluate → save → fire callback (T2.5)."""

import asyncio
import logging
from datetime import datetime, timezone

from rest_assured.src.models.services import Service
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.scheduler.evaluate import evaluate_response

logger = logging.getLogger(__name__)


async def worker_loop(runner, service: Service) -> None:
    """
    Бесконечный цикл проверки одного сервиса (T2.5).

    Args:
        runner: Экземпляр SchedulerRunner.
        service: Сервис для мониторинга.
    """
    log = logger.getChild(f"worker_{service.id}")
    interval_seconds = service.interval_ms / 1000.0

    while True:
        try:
            await asyncio.sleep(interval_seconds)

            t_start = datetime.now(timezone.utc)
            try:
                resp = await runner.http_client.request(
                    method=service.http_method,
                    url=service.url,
                )
                latency_ms = int(
                    (datetime.now(timezone.utc) - t_start).total_seconds() * 1000
                )
                check = evaluate_response(
                    service, response=resp, latency_ms=latency_ms
                )
            except Exception as exc:
                latency_ms = int(
                    (datetime.now(timezone.utc) - t_start).total_seconds() * 1000
                )
                check = evaluate_response(
                    service, exception=exc, latency_ms=latency_ms
                )

            # Сохранить результат в БД
            session = get_session()
            try:
                session.add(check)
                await session.commit()
                await session.refresh(check)
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

            # Обновить счётчики
            runner.checks_total += 1
            if not check.is_up:
                runner.checks_failed += 1
            runner.last_loop_at = datetime.now(timezone.utc)

            # Вызвать коллбэки (Эпик 4 — incidents/notifications)
            await runner.fire_callbacks(check)

            log.debug(
                "checked: is_up=%s, status=%s, latency=%sms",
                check.is_up,
                check.http_status,
                latency_ms,
            )

        except asyncio.CancelledError:
            log.info("worker cancelled")
            raise
        except Exception as e:
            log.error("worker iteration failed: %s", e)
            await asyncio.sleep(5)  # пауза перед повтором после ошибки