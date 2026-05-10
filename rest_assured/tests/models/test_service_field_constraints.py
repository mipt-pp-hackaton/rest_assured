"""Тесты ограничений полей модели Service (T10)."""

import socket

import pytest
from pydantic import ValidationError

from rest_assured.src.models.services import Service


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch):
    def _ok(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port or 80))]

    monkeypatch.setattr(socket, "getaddrinfo", _ok)


def test_interval_below_1000_rejected():
    with pytest.raises(ValidationError):
        Service(name="x", url="http://example.com", interval_ms=500)


def test_interval_1000_ok():
    s = Service(name="x", url="http://example.com", interval_ms=1000)
    assert s.interval_ms == 1000


def test_name_max_length():
    with pytest.raises(ValidationError):
        Service(name="a" * 256, url="http://example.com")


def test_url_max_length():
    long = "http://" + "a" * 2050 + ".com"
    with pytest.raises(ValidationError):
        Service(name="x", url=long)


def test_http_method_invalid():
    with pytest.raises(ValidationError):
        Service(name="x", url="http://example.com", http_method="TRACE")


@pytest.mark.parametrize("m", ["GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"])
def test_http_method_valid(m):
    s = Service(name="x", url="http://example.com", http_method=m)
    assert s.http_method == m
