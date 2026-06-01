"""Тесты новых TLS/timeout-полей SmtpConfig (готовность к внешнему SMTP)."""

from rest_assured.src.configs.app.smtp import SmtpConfig


def _make_config(**overrides) -> SmtpConfig:
    base = {
        "host": "smtp.example.com",
        "from_email": "noreply@example.com",
        "from_name": "Rest Assured",
    }
    base.update(overrides)
    return SmtpConfig(**base)


def test_tls_defaults_are_safe():
    cfg = _make_config()
    assert cfg.use_tls is False
    assert cfg.start_tls is None  # оппортунистический STARTTLS
    assert cfg.validate_certs is True
    assert cfg.timeout_seconds == 30


def test_implicit_tls_config_for_external_provider():
    """Yandex/Gmail-стиль: implicit TLS на 465."""
    cfg = _make_config(port=465, use_tls=True, user="u@yandex.ru", password="x")
    assert cfg.use_tls is True
    assert cfg.port == 465


def test_starttls_config_for_587():
    cfg = _make_config(port=587, start_tls=True)
    assert cfg.start_tls is True
    assert cfg.use_tls is False
