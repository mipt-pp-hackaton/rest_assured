"""Тесты для evaluator."""

import pytest
from rest_assured.src.scheduler.evaluator import evaluate_response


@pytest.mark.parametrize(
    "status_code,error,expected",
    [
        (200, None, True),
        (201, None, True),
        (301, None, True),
        (404, None, True),
        (499, None, True),
        (500, None, False),
        (502, None, False),
        (503, None, False),
        (None, "timeout", False),
        (None, "connection refused", False),
        (200, "unexpected error", False),
    ],
)
def test_evaluate_response(status_code, error, expected):
    """Проверяет классификацию HTTP-ответов."""
    assert evaluate_response(status_code, error) == expected