"""Тесты валидатора URL для модели Service (T10).

Приватные/«серые» IP теперь разрешены — инструмент штатно мониторит и
внутренние сервисы. Валидатор проверяет только схему (http/https) и
резолвимость hostname; диапазон IP не ограничивается.
"""

import socket

import pytest

from rest_assured.src.models.services import validate_public_url


def _mock_resolve_to(ip: str):
    def _fake(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 0, "", (ip, port or 80))]

    return _fake


@pytest.mark.parametrize(
    "url,ip",
    [
        ("http://example.com", "93.184.216.34"),
        ("https://api.example.com:8443/path", "93.184.216.34"),
        # Приватные/«серые», loopback и link-local теперь принимаются.
        ("http://10.0.0.1", "10.0.0.1"),
        ("http://172.16.0.1", "172.16.0.1"),
        ("http://192.168.1.1", "192.168.1.1"),
        ("http://127.0.0.1", "127.0.0.1"),
        ("http://169.254.169.254", "169.254.169.254"),
        ("http://[::1]", "::1"),
        ("http://[fe80::1]", "fe80::1"),
    ],
)
def test_validate_accepts_resolvable(monkeypatch, url, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _mock_resolve_to(ip))
    assert validate_public_url(url) == url


@pytest.mark.parametrize(
    "url",
    ["ftp://example.com", "file:///etc/passwd", "ws://example.com"],
)
def test_validate_rejects_bad_scheme(monkeypatch, url):
    monkeypatch.setattr(socket, "getaddrinfo", _mock_resolve_to("93.184.216.34"))
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_validate_rejects_no_hostname():
    with pytest.raises(ValueError):
        validate_public_url("http://")


def test_validate_rejects_unresolvable(monkeypatch):
    def _boom(*args, **kwargs):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    with pytest.raises(ValueError):
        validate_public_url("http://does-not-exist.invalid")
