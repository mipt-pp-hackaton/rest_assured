"""T16: sanitize log helper экранирует управляющие символы и обрезает payload."""

from rest_assured.src.scheduler.listener import _sanitize_log


def test_newline_is_escaped():
    out = _sanitize_log("1\nFAKE: hacked")
    assert "\n" not in out
    assert "\\n" in out


def test_truncate_long_payload():
    out = _sanitize_log("a" * 1000, limit=50)
    # encode("unicode_escape") может растянуть, но не сильно. Главное — не вся строка.
    assert len(out) <= 200


def test_control_chars_are_escaped():
    out = _sanitize_log("\r\tINJECT")
    assert "\r" not in out
    assert "\t" not in out


def test_plain_ascii_passthrough():
    out = _sanitize_log("123")
    assert out == "123"
