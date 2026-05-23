"""RED-phase tests for Fix B — SmtpConfig.password must be ``pydantic.SecretStr``.

Mirrors the pattern used in ``test_jwt_config.py::test_jwt_secret_is_secret_str``.
"""

from __future__ import annotations

from pydantic import SecretStr

from rest_assured.src.configs.app.smtp import SmtpConfig


def _make_config(**overrides) -> SmtpConfig:
    """Construct a SmtpConfig with sensible required defaults overlaid by kwargs."""
    base = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "noreply@example.com",
        "password": "super-secret-smtp-value",
        "use_tls": True,
        "from_email": "noreply@example.com",
        "from_name": "Rest Assured",
    }
    base.update(overrides)
    return SmtpConfig(**base)


# ---------------------------------------------------------------------------
# AC #1 — type is SecretStr after construction
# ---------------------------------------------------------------------------
def test_smtp_password_is_secret_str() -> None:
    cfg = _make_config()
    assert type(cfg.password) is SecretStr


# ---------------------------------------------------------------------------
# AC #2 — repr / model_dump must not leak the raw secret
# ---------------------------------------------------------------------------
def test_smtp_password_not_leaked_in_repr() -> None:
    cfg = _make_config(password="super-secret-smtp-value")
    assert "super-secret-smtp-value" not in repr(cfg)
    assert "super-secret-smtp-value" not in repr(cfg.password)


def test_smtp_password_not_leaked_in_model_dump() -> None:
    cfg = _make_config(password="super-secret-smtp-value")
    dumped = cfg.model_dump()
    assert "super-secret-smtp-value" not in str(dumped)


# ---------------------------------------------------------------------------
# AC #3 — round-trip via get_secret_value
# ---------------------------------------------------------------------------
def test_smtp_password_round_trips_via_get_secret_value() -> None:
    cfg = _make_config(password="super-secret-smtp-value")
    assert cfg.password.get_secret_value() == "super-secret-smtp-value"


# ---------------------------------------------------------------------------
# AC #4 — defaults to an empty SecretStr when not supplied
# ---------------------------------------------------------------------------
def test_smtp_password_defaults_to_empty_secret_str() -> None:
    cfg = SmtpConfig(
        host="smtp.example.com",
        from_email="noreply@example.com",
        from_name="Rest Assured",
    )
    assert type(cfg.password) is SecretStr
    assert cfg.password.get_secret_value() == ""
