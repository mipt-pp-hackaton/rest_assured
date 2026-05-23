"""Unit tests for `rest_assured.src.services.auth.jwt` (T6).

These tests cover the new T6 API:
- `create_access_token(subject, *, ttl=None)` with embedded `token_type="access"`.
- `create_refresh_token(subject, *, ttl=None)` with embedded `token_type="refresh"`.
- `decode_token(token, *, expected_type)` returning a typed `TokenPayload`.
- Various 401 error paths (bad signature, expired, missing `sub`,
  mismatched `token_type`, manually-crafted `alg=none` header).
"""

from __future__ import annotations

import base64
import json
from datetime import timedelta

import jwt as jose_jwt
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from rest_assured.src.configs.app.main import settings
from rest_assured.src.services.auth import jwt as jwt_module

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_SECRET = "unit-test-secret-do-not-use-in-prod"
_TEST_ALG = "HS256"
_ACCESS_TTL_MIN = 15
_REFRESH_TTL_DAYS = 7


@pytest.fixture(autouse=True)
def _jwt_settings(monkeypatch):
    """Force a deterministic JWT config for the duration of each test.

    Tests must not depend on whatever happens to live in `settings.toml`.
    We replace the entire `settings.jwt` config with a fresh object so that
    both the legacy ``str`` secret and the new ``SecretStr`` secret produce
    consistent behaviour for the unit under test.
    """

    class _StubJWT:
        secret = SecretStr(_TEST_SECRET)
        algorithm = _TEST_ALG
        access_token_ttl_minutes = _ACCESS_TTL_MIN
        refresh_token_ttl_days = _REFRESH_TTL_DAYS
        # Legacy field, kept for backwards-compat with T2's deprecation notice.
        ttl_hours = 24

    monkeypatch.setattr(settings, "jwt", _StubJWT(), raising=True)
    return _StubJWT


def _decode_raw(token: str) -> dict:
    """Decode a token using the test secret directly (no validation logic)."""
    return jose_jwt.decode(token, _TEST_SECRET, algorithms=[_TEST_ALG])


# ---------------------------------------------------------------------------
# create_access_token / create_refresh_token
# ---------------------------------------------------------------------------


def test_create_access_token_sets_token_type_access():
    """AC1: decode(create_access_token(...)) -> token_type == 'access'."""
    token = jwt_module.create_access_token("u@x")
    payload = _decode_raw(token)
    assert payload["token_type"] == "access"


def test_create_refresh_token_sets_token_type_refresh():
    """AC2: decode(create_refresh_token(...)) -> token_type == 'refresh'."""
    token = jwt_module.create_refresh_token("u@x")
    payload = _decode_raw(token)
    assert payload["token_type"] == "refresh"


def test_create_access_token_default_ttl_matches_settings():
    """AC3: default access ttl ~= settings.jwt.access_token_ttl_minutes * 60."""
    token = jwt_module.create_access_token("u@x")
    payload = _decode_raw(token)
    expected = _ACCESS_TTL_MIN * 60
    delta = payload["exp"] - payload["iat"]
    assert (
        abs(delta - expected) <= 2
    ), f"access ttl {delta}s differs from expected {expected}s by more than 2s"


def test_create_refresh_token_default_ttl_matches_settings():
    """AC4: default refresh ttl ~= settings.jwt.refresh_token_ttl_days * 86400."""
    token = jwt_module.create_refresh_token("u@x")
    payload = _decode_raw(token)
    expected = _REFRESH_TTL_DAYS * 86400
    delta = payload["exp"] - payload["iat"]
    assert (
        abs(delta - expected) <= 2
    ), f"refresh ttl {delta}s differs from expected {expected}s by more than 2s"


def test_tokens_carry_sub_iat_exp_and_token_type_claims():
    """AC5: both tokens carry sub, iat, exp, token_type claims."""
    access = jwt_module.create_access_token("u@x")
    refresh = jwt_module.create_refresh_token("u@x")

    for token, expected_type in [(access, "access"), (refresh, "refresh")]:
        payload = _decode_raw(token)
        assert payload.get("sub") == "u@x"
        assert isinstance(payload.get("iat"), int)
        assert isinstance(payload.get("exp"), int)
        assert payload.get("token_type") == expected_type


def test_create_access_token_accepts_int_subject_and_stringifies():
    """`subject: str | int` — int subject must be coerced to str in `sub`."""
    token = jwt_module.create_access_token(42)
    payload = _decode_raw(token)
    assert payload["sub"] == "42"
    assert isinstance(payload["sub"], str)


def test_create_access_token_custom_ttl_overrides_default():
    """Explicit `ttl=` overrides `settings.jwt.access_token_ttl_minutes`."""
    token = jwt_module.create_access_token("u@x", ttl=timedelta(seconds=120))
    payload = _decode_raw(token)
    delta = payload["exp"] - payload["iat"]
    assert abs(delta - 120) <= 2


# ---------------------------------------------------------------------------
# decode_token
# ---------------------------------------------------------------------------


def test_decode_token_returns_typed_payload_for_valid_access_token():
    """AC6: decode_token(t, expected_type='access') returns TokenPayload with
    sub == 'u@x' and token_type == 'access'."""
    token = jwt_module.create_access_token("u@x")
    payload = jwt_module.decode_token(token, expected_type="access")

    # Support either pydantic-model-style or dict-style payloads.
    sub = getattr(payload, "sub", None) if not isinstance(payload, dict) else payload.get("sub")
    token_type = (
        getattr(payload, "token_type", None)
        if not isinstance(payload, dict)
        else payload.get("token_type")
    )
    assert sub == "u@x"
    assert token_type == "access"

    # And there should be a `TokenPayload` type exported.
    assert hasattr(jwt_module, "TokenPayload")


def test_decode_token_rejects_refresh_when_expected_access():
    """AC7: decoding a refresh token with expected_type='access' -> 401."""
    refresh = jwt_module.create_refresh_token("u@x")
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(refresh, expected_type="access")
    assert exc.value.status_code == 401
    assert "invalid token type" in str(exc.value.detail).lower()


def test_decode_token_rejects_access_when_expected_refresh():
    """Mirror of AC7: access token with expected_type='refresh' -> 401."""
    access = jwt_module.create_access_token("u@x")
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(access, expected_type="refresh")
    assert exc.value.status_code == 401
    assert "invalid token type" in str(exc.value.detail).lower()


def test_decode_token_rejects_expired_token():
    """AC8: expired token -> 401 with expiry-related detail."""
    expired = jwt_module.create_access_token("u@x", ttl=timedelta(seconds=-60))
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(expired, expected_type="access")
    assert exc.value.status_code == 401
    # jose surfaces expiry as "Signature has expired" — accept any 401 whose
    # detail mentions expiry, or generic "could not validate credentials".
    detail = str(exc.value.detail).lower()
    assert "expire" in detail or "credentials" in detail


def test_decode_token_rejects_bad_signature(monkeypatch):
    """AC9: token signed with a different secret -> 401."""
    foreign = jose_jwt.encode(
        {"sub": "u@x", "iat": 0, "exp": 9999999999, "token_type": "access"},
        "totally-different-secret",
        algorithm=_TEST_ALG,
    )
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(foreign, expected_type="access")
    assert exc.value.status_code == 401


def test_decode_token_rejects_alg_none_unsigned_token():
    """AC10: a hand-crafted `alg=none` token -> 401.

    `jose.jwt.encode` won't emit an unsigned token directly, so we assemble
    the three-part `header.payload.` structure manually. With
    `algorithms=[settings.jwt.algorithm]` (no "none"), jose must refuse it.
    """
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "u@x", "iat": 0, "exp": 9999999999, "token_type": "access"}

    def _b64url(obj: dict) -> str:
        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    unsigned = f"{_b64url(header)}.{_b64url(payload)}."

    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(unsigned, expected_type="access")
    assert exc.value.status_code == 401


def test_decode_token_rejects_token_without_sub():
    """AC11: payload omits `sub` -> 401."""
    token_without_sub = jose_jwt.encode(
        {"iat": 0, "exp": 9999999999, "token_type": "access"},
        _TEST_SECRET,
        algorithm=_TEST_ALG,
    )
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(token_without_sub, expected_type="access")
    assert exc.value.status_code == 401


def test_decode_token_rejects_token_without_token_type_claim():
    """`token_type` missing -> 401 (claim is mandatory after T6)."""
    legacy_shaped = jose_jwt.encode(
        {"sub": "u@x", "iat": 0, "exp": 9999999999},  # no token_type
        _TEST_SECRET,
        algorithm=_TEST_ALG,
    )
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(legacy_shaped, expected_type="access")
    assert exc.value.status_code == 401


def test_decode_token_rejects_token_without_iat():
    """A signed token without `iat` must not 500 — defensive 401 instead.

    jose validates `exp` but does not require `iat` to be present, so a token
    crafted without `iat` would previously trip a KeyError in `decode_token`
    when building the TokenPayload. The defensive guard should turn this into
    an HTTP 401 mentioning the missing claim.
    """
    token = jose_jwt.encode(
        {"sub": "u@x", "exp": 9999999999, "token_type": "access"},  # no iat
        _TEST_SECRET,
        algorithm=_TEST_ALG,
    )
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(token, expected_type="access")
    assert exc.value.status_code == 401
    assert "exp/iat" in str(exc.value.detail).lower()


def test_decode_token_rejects_token_without_exp():
    """A signed token without `exp` must still be refused with 401.

    Depending on jose version, the library may itself reject tokens missing
    `exp` — in either case the resulting status must be 401, never 500.
    """
    token = jose_jwt.encode(
        {"sub": "u@x", "iat": 0, "token_type": "access"},  # no exp
        _TEST_SECRET,
        algorithm=_TEST_ALG,
    )
    with pytest.raises(HTTPException) as exc:
        jwt_module.decode_token(token, expected_type="access")
    assert exc.value.status_code == 401
