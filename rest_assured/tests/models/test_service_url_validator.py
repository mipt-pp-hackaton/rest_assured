"""Тесты валидатора URL для модели Service (SSRF-защита, T10)."""

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
    ],
)
def test_validate_accepts_public(monkeypatch, url, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _mock_resolve_to(ip))
    assert validate_public_url(url) == url


@pytest.mark.parametrize(
    "url,ip,reason",
    [
        ("ftp://example.com", "93.184.216.34", "scheme"),
        ("file:///etc/passwd", "93.184.216.34", "scheme"),
        ("http://127.0.0.1", "127.0.0.1", "loopback"),
        ("http://10.0.0.1", "10.0.0.1", "private"),
        ("http://172.16.0.1", "172.16.0.1", "private"),
        ("http://192.168.1.1", "192.168.1.1", "private"),
        ("http://169.254.169.254", "169.254.169.254", "link-local"),
        ("http://[::1]", "::1", "ipv6-loopback"),
        ("http://[fe80::1]", "fe80::1", "ipv6-link-local"),
    ],
)
def test_validate_rejects_unsafe(monkeypatch, url, ip, reason):
    monkeypatch.setattr(socket, "getaddrinfo", _mock_resolve_to(ip))
    with pytest.raises(ValueError):
        validate_public_url(url)
