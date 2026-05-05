import httpx
import pytest
from rest_assured.src.scheduler.evaluator import evaluate_response


class FakeResponse:
    """Имитация httpx.Response для тестов."""
    def __init__(self, status_code: int, elapsed_ms: int = 100):
        self.status_code = status_code
        self._elapsed_ms = elapsed_ms

    @property
    def elapsed(self):
        import datetime
        return datetime.timedelta(milliseconds=self._elapsed_ms)


def test_evaluate_response_success():
    """2xx ответ — сервис доступен."""
    resp = FakeResponse(200, elapsed_ms=50)
    result = evaluate_response(resp)
    assert result["is_up"] is True
    assert result["status_code"] == 200
    assert result["response_time_ms"] == 50
    assert result["error_message"] is None


def test_evaluate_response_client_error():
    """4xx ответ — сервис доступен (не серверная ошибка)."""
    resp = FakeResponse(404, elapsed_ms=30)
    result = evaluate_response(resp)
    assert result["is_up"] is True
    assert result["status_code"] == 404
    assert result["error_message"] is None


def test_evaluate_response_server_error():
    """5xx ответ — сервис недоступен."""
    resp = FakeResponse(500, elapsed_ms=120)
    result = evaluate_response(resp)
    assert result["is_up"] is False
    assert result["status_code"] == 500
    assert result["response_time_ms"] == 120
    assert "Server error: 500" in result["error_message"]


def test_evaluate_response_with_error():
    """Исключение при запросе — сервис недоступен."""
    error = Exception("Connection timeout")
    result = evaluate_response(None, error=error)
    assert result["is_up"] is False
    assert result["status_code"] is None
    assert result["response_time_ms"] is None
    assert result["error_message"] == "Connection timeout"


def test_evaluate_response_none():
    """Нет ни ответа, ни ошибки."""
    result = evaluate_response(None)
    assert result["is_up"] is False
    assert result["error_message"] == "No response received"
