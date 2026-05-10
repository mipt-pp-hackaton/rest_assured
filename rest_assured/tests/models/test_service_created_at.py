"""Тесты на UTC-aware created_at у Service (T10)."""

import socket
from datetime import datetime, timezone

from rest_assured.src.models.services import Service


def test_created_at_is_utc_aware(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda h, p, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", p or 80))
        ],
    )
    s = Service(name="x", url="http://example.com")
    assert s.created_at.tzinfo is not None
    assert s.created_at.utcoffset().total_seconds() == 0
    assert abs((datetime.now(timezone.utc) - s.created_at).total_seconds()) < 1
