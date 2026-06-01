"""Логирование приложения на базе loguru.

По умолчанию включён **структурированный JSON-вывод** (loguru ``serialize``):
stdlib-логи (планировщик использует stdlib ``logging``) и uvicorn заворачиваются
в единый JSON-поток через ``_InterceptHandler`` — пригодно для сбора в
ELK / Loki / Datadog. Отключается через ``DYNACONF_LOGGING__JSON_LOGS=false``.

Под pytest ``configure_logging`` ничего не трогает: scheduler-тесты ловят
stdlib-логи через ``caplog`` (см. CLAUDE.md), а перехват сломал бы их. JSON-путь
проверяется отдельным smoke-тестом вне pytest.
"""

import logging
import sys

from loguru import logger

__all__ = ["logger", "configure_logging"]


class _InterceptHandler(logging.Handler):
    """Перенаправляет записи stdlib ``logging`` в loguru (стандартный рецепт)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # bind(logger=...) сохраняет исходное имя stdlib-логгера (компонент) в
        # extra — depth-эвристика loguru не всегда восстанавливает его в name.
        logger.opt(depth=depth, exception=record.exc_info).bind(logger=record.name).log(
            level, record.getMessage()
        )


def configure_logging(*, json_logs: bool = True, level: str = "INFO") -> None:
    """Настроить логирование. JSON по умолчанию; под pytest — no-op."""
    # Под pytest не вмешиваемся в логирование (иначе ломается caplog в
    # scheduler-тестах, которые рассчитывают на stdlib logging).
    if "pytest" in sys.modules:
        return
    if not json_logs:
        return

    logger.remove()
    # diagnose=False — не печатать значения переменных в traceback (могут быть секреты).
    logger.add(sys.stderr, level=level, serialize=True, backtrace=False, diagnose=False)

    # Завернуть stdlib-логи (планировщик, uvicorn) в loguru → единый JSON-поток.
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.NOTSET, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = []
        std_logger.propagate = True
