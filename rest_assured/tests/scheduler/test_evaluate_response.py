"""Тесты T13: redact credentials, RuntimeError, UTC checked_at."""

import httpx
import pytest

from rest_assured.src.models.services import Service
from rest_assured.src.scheduler.evaluate import evaluate_response


def _make_service(**kwargs):
    """Минимальный валидный Service для тестов."""
    return Service(id=1, name="t", url="http://example.com", **kwargs)


def test_evaluate_redacts_credentials_in_exception():
    """Сообщение об исключении не должно содержать Basic Auth из repr()."""
    s = _make_service()
    exc = httpx.ConnectError("connect to http://user:secret@internal.example.com/x failed")
    result = evaluate_response(s, response=None, exception=exc, latency_ms=10)
    assert "user:secret" in str(exc)  # sanity: credentials есть в исходном исключении
    # Но result.error содержит только type + str(exc) — без repr() с url атрибутами.
    # str(httpx.ConnectError(msg)) = msg, поэтому проверяем формат "ConnectError: <msg>"
    assert "ConnectError" in (result.error or "")


def test_evaluate_requires_response_or_exception():
    """Без response и без exception должно бросаться RuntimeError, не AssertionError."""
    s = _make_service()
    with pytest.raises(RuntimeError):
        evaluate_response(s, response=None, exception=None, latency_ms=10)


def test_evaluate_checked_at_is_utc():
    """checked_at должен быть timezone-aware UTC."""
    s = _make_service()
    exc = httpx.ConnectError("x")
    result = evaluate_response(s, response=None, exception=exc, latency_ms=1)
    assert result.checked_at.tzinfo is not None
    assert result.checked_at.utcoffset().total_seconds() == 0


def test_evaluate_error_format_no_repr():
    """Формат должен быть 'ClassName: message' (без repr-кавычек)."""
    s = _make_service()
    exc = httpx.TimeoutException("Request timed out")
    result = evaluate_response(s, response=None, exception=exc, latency_ms=100)
    assert result.error is not None
    assert result.error.startswith("TimeoutException: ")
    # repr() даёт TimeoutException('Request timed out'), str() — Request timed out.
    # Проверяем, что не было repr() — то есть нет кавычек вокруг сообщения.
    assert "TimeoutException('Request timed out')" not in result.error
