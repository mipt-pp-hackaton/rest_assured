"""Тесты для evaluate_response (T2.6)."""

from unittest.mock import MagicMock

import httpx
import pytest

from rest_assured.src.models.services import Service
from rest_assured.src.scheduler.evaluate import evaluate_response


def create_test_service(expected_status=None):
    """Создаёт тестовый Service с int id."""
    s = MagicMock(spec=Service)
    s.id = 1  # int, согласно контракту
    s.url = "http://test.com"
    s.name = "Test Service"
    s.http_method = "GET"
    s.interval_ms = 60000
    s.expected_status = expected_status
    s.is_active = True
    return s


def create_mock_response(status_code: int):
    """Создаёт мок httpx.Response с заданным status_code."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    return response


@pytest.mark.parametrize(
    "expected,actual,is_up",
    [
        (200, 200, True),
        (200, 500, False),
        (200, 404, False),
        (None, 200, True),
        (None, 201, True),
        (None, 299, True),
        (None, 300, False),
        (None, 400, False),
        (None, 500, False),
        (404, 404, True),
        (404, 200, False),
    ],
)
def test_evaluate_response_status(expected, actual, is_up):
    service = create_test_service(expected_status=expected)
    response = create_mock_response(actual)

    result = evaluate_response(service, response=response, latency_ms=100)

    assert result.is_up == is_up
    assert result.http_status == actual
    assert result.latency_ms == 100
    assert result.service_id == 1


def test_evaluate_response_timeout():
    service = create_test_service()
    exception = httpx.TimeoutException("Request timed out")

    result = evaluate_response(service, exception=exception, latency_ms=5000)

    assert result.is_up is False
    assert result.http_status is None
    assert "TimeoutException" in result.error


def test_evaluate_response_connection_error():
    service = create_test_service()
    exception = httpx.ConnectError("Connection refused")

    result = evaluate_response(service, exception=exception, latency_ms=0)

    assert result.is_up is False
    assert result.http_status is None
    assert "ConnectError" in result.error
