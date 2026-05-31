"""Тесты валидации request-DTO сервисов.

Закрывают gap «схема vs модель»: невалидный ввод должен отсекаться на разборе
запроса (pydantic.ValidationError → FastAPI вернёт 422), а не падать позже при
конструировании модели в репозитории (что давало 500).

DNS-резолвинг внутри validate_public_url под pytest пропускается (проверяются
только схема и наличие hostname), поэтому моки сети не нужны.
"""

import pytest
from pydantic import ValidationError

from rest_assured.src.schemas.services import ServiceCreate, ServiceUpdate


def test_create_accepts_valid():
    s = ServiceCreate(url="http://example.com", name="svc", interval_ms=1000)
    assert s.url == "http://example.com"
    assert s.interval_ms == 1000
    assert s.owner_emails == []


def test_create_accepts_owner_emails():
    s = ServiceCreate(
        url="http://example.com",
        name="svc",
        owner_emails=["ops@example.com", "lead@example.com"],
    )
    assert s.owner_emails == ["ops@example.com", "lead@example.com"]


def test_create_rejects_bad_owner_email():
    with pytest.raises(ValidationError):
        ServiceCreate(url="http://example.com", name="svc", owner_emails=["not-an-email"])


def test_update_rejects_bad_owner_email():
    with pytest.raises(ValidationError):
        ServiceUpdate(owner_emails=["nope"])


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"url": "ftp://example.com", "name": "x"}, "bad-scheme"),
        ({"url": "notaurl", "name": "x"}, "no-hostname"),
        ({"url": "http://example.com", "name": "x", "interval_ms": 500}, "interval<1000"),
        ({"url": "http://example.com", "name": "x", "interval_ms": 0}, "interval=0"),
        ({"url": "http://example.com", "name": "n" * 256}, "name>255"),
        ({"url": "http://" + "a" * 2049, "name": "x"}, "url>2048"),
    ],
)
def test_create_rejects_invalid(kwargs, reason):
    with pytest.raises(ValidationError):
        ServiceCreate(**kwargs)


def test_update_allows_empty_and_none():
    u = ServiceUpdate()
    assert u.url is None and u.interval_ms is None and u.name is None


def test_update_accepts_valid_partial():
    u = ServiceUpdate(interval_ms=5000)
    assert u.interval_ms == 5000


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"url": "ftp://x"}, "bad-scheme"),
        ({"url": "garbage"}, "no-hostname"),
        ({"interval_ms": 500}, "interval<1000"),
        ({"name": "n" * 256}, "name>255"),
    ],
)
def test_update_rejects_invalid(kwargs, reason):
    with pytest.raises(ValidationError):
        ServiceUpdate(**kwargs)
