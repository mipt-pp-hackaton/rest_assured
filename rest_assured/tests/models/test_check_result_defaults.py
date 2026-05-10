from datetime import datetime, timezone

from rest_assured.src.models.checks import CheckResult


def test_checked_at_is_utc_aware():
    r = CheckResult(service_id=1, is_up=True, http_status=200, latency_ms=10)
    assert r.checked_at.tzinfo is not None
    assert r.checked_at.utcoffset().total_seconds() == 0
    # within ~1 second of now
    delta = abs((datetime.now(timezone.utc) - r.checked_at).total_seconds())
    assert delta < 1.0
