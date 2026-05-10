"""Классификация HTTP-ответов (T2.6)."""

from datetime import datetime

import httpx

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service


def evaluate_response(
    service: Service,
    *,
    response: httpx.Response | None = None,
    exception: Exception | None = None,
    latency_ms: int = 0,
) -> CheckResult:
    """
    Оценивает результат HTTP-запроса и создает CheckResult.

    Правила (T2.6):
    - Нет исключения AND (status_code == expected_status OR
      (expected_status IS NULL AND 200 <= status < 300)) → is_up = True
    - Иначе → is_up = False
    """
    now = datetime.utcnow()

    if exception is not None:
        return CheckResult(
            service_id=service.id,
            checked_at=now,
            is_up=False,
            http_status=None,
            latency_ms=latency_ms,
            error=_truncate(repr(exception)),
        )

    assert response is not None, "Either response or exception must be provided"
    status = response.status_code

    if service.expected_status is not None:
        is_up = status == service.expected_status
        error_msg = (
            None if is_up else f"unexpected status {status} (expected {service.expected_status})"
        )
    else:
        is_up = 200 <= status < 300
        error_msg = None if is_up else f"unexpected status {status} (expected 2xx)"

    return CheckResult(
        service_id=service.id,
        checked_at=now,
        is_up=is_up,
        http_status=status,
        latency_ms=latency_ms,
        error=error_msg,
    )


def _truncate(s: str, max_length: int = 500) -> str:
    """Обрезает строку до max_length."""
    return s[:max_length]
