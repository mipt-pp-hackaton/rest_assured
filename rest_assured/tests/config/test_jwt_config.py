"""RED-phase tests for task T2 — extending JWTConfig with access/refresh TTLs.

Acceptance criteria mirror TASKS.md T2:
1. Values from TOML map to ``access_token_ttl_minutes`` / ``refresh_token_ttl_days``.
2. ``secret`` is ``pydantic.SecretStr``.
3. Defaults: algorithm="HS256", access_token_ttl_minutes=15, refresh_token_ttl_days=14.
4. ``algorithm="none"`` (any casing) is rejected via pydantic ValidationError / ValueError.
"""

from __future__ import annotations

import tomllib

import pytest
from pydantic import SecretStr, ValidationError

from rest_assured.src.configs.app.jwt import JWTConfig


# ---------------------------------------------------------------------------
# AC #1 — TOML values surface on the JWTConfig instance
# ---------------------------------------------------------------------------
def test_jwt_config_loads_access_and_refresh_ttls_from_toml() -> None:
    toml_text = """
    [jwt]
    secret = "x"
    algorithm = "HS256"
    access_token_ttl_minutes = 15
    refresh_token_ttl_days = 14
    """
    data = tomllib.loads(toml_text)
    cfg = JWTConfig(**data["jwt"])

    assert cfg.access_token_ttl_minutes == 15
    assert cfg.refresh_token_ttl_days == 14
    assert cfg.algorithm == "HS256"


def test_jwt_config_loads_custom_ttls_from_toml() -> None:
    """Round-trip non-default values to confirm the field is wired, not hard-coded."""
    toml_text = """
    [jwt]
    secret = "x"
    algorithm = "HS256"
    access_token_ttl_minutes = 42
    refresh_token_ttl_days = 7
    """
    data = tomllib.loads(toml_text)
    cfg = JWTConfig(**data["jwt"])

    assert cfg.access_token_ttl_minutes == 42
    assert cfg.refresh_token_ttl_days == 7


# ---------------------------------------------------------------------------
# AC #2 — secret is SecretStr
# ---------------------------------------------------------------------------
def test_jwt_secret_is_secret_str() -> None:
    cfg = JWTConfig(secret="x")
    assert type(cfg.secret) is SecretStr
    assert cfg.secret.get_secret_value() == "x"


def test_jwt_secret_not_leaked_in_repr() -> None:
    cfg = JWTConfig(secret="super-confidential-value")
    assert "super-confidential-value" not in repr(cfg)
    assert "super-confidential-value" not in repr(cfg.secret)


# ---------------------------------------------------------------------------
# AC #3 — defaults
# ---------------------------------------------------------------------------
def test_jwt_default_algorithm_is_hs256() -> None:
    cfg = JWTConfig(secret="x")
    assert cfg.algorithm == "HS256"


def test_jwt_default_access_token_ttl_minutes_is_15() -> None:
    cfg = JWTConfig(secret="x")
    assert cfg.access_token_ttl_minutes == 15


def test_jwt_default_refresh_token_ttl_days_is_14() -> None:
    cfg = JWTConfig(secret="x")
    assert cfg.refresh_token_ttl_days == 14


# ---------------------------------------------------------------------------
# AC #4 — "none" algorithm rejected (case-insensitive)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_alg", ["none", "NONE", "None", "NoNe", "nOnE"])
def test_jwt_algorithm_none_is_rejected(bad_alg: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        JWTConfig(secret="x", algorithm=bad_alg)


def test_jwt_algorithm_hs256_is_accepted() -> None:
    """Sanity check: a sane algorithm must still work after the validator is added."""
    cfg = JWTConfig(secret="x", algorithm="HS256")
    assert cfg.algorithm == "HS256"
