"""RED-phase tests for T5: Pydantic schemas for register / refresh / current-user.

These tests are written BEFORE the schemas exist. They must fail with
ImportError / ModuleNotFoundError until the developer creates:

    rest_assured/src/schemas/users.py  -> UserCreate, UserRead
    rest_assured/src/schemas/auth.py   -> TokenPair, RefreshRequest

Acceptance criteria are enumerated in Task T5 [CODE].
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

# ----------------------------------------------------------------------
# UserCreate
# ----------------------------------------------------------------------


def test_user_create_valid_defaults_is_superuser_false():
    """AC1: Valid input constructs; is_superuser defaults to False."""
    from rest_assured.src.schemas.users import UserCreate

    obj = UserCreate(email="a@b.com", password="abcdefgh")
    assert obj.email == "a@b.com"
    assert obj.password == "abcdefgh"
    assert obj.is_superuser is False


def test_user_create_invalid_email_raises():
    """AC2: Invalid email raises ValidationError."""
    from rest_assured.src.schemas.users import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="abcdefgh")


def test_user_create_short_password_raises():
    """AC3: Password shorter than 8 chars raises ValidationError."""
    from rest_assured.src.schemas.users import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="short")


def test_user_create_explicit_is_superuser_true():
    """AC4: is_superuser=True accepted explicitly."""
    from rest_assured.src.schemas.users import UserCreate

    obj = UserCreate(email="admin@b.com", password="abcdefgh", is_superuser=True)
    assert obj.is_superuser is True


# ----------------------------------------------------------------------
# UserRead
# ----------------------------------------------------------------------


def _user_read_kwargs():
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "email": "a@b.com",
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }


def test_user_read_constructs_with_all_fields():
    """AC5: UserRead constructs from id/email/is_active/is_superuser/created_at/updated_at."""
    from rest_assured.src.schemas.users import UserRead

    kwargs = _user_read_kwargs()
    obj = UserRead(**kwargs)
    assert obj.id == 1
    assert obj.email == "a@b.com"
    assert obj.is_active is True
    assert obj.is_superuser is False
    assert obj.created_at == kwargs["created_at"]
    assert obj.updated_at == kwargs["updated_at"]


def test_user_read_does_not_expose_password_hash():
    """AC6: UserRead must NOT declare a password_hash field."""
    from rest_assured.src.schemas.users import UserRead

    assert "password_hash" not in UserRead.model_fields


def test_user_read_has_from_attributes_enabled():
    """AC7: from_attributes (orm-mode) is on so it can be built from a SQLModel row."""
    from rest_assured.src.schemas.users import UserRead

    assert UserRead.model_config.get("from_attributes") is True


# ----------------------------------------------------------------------
# TokenPair
# ----------------------------------------------------------------------


def test_token_pair_constructs_with_default_token_type():
    """AC8: TokenPair constructs; token_type defaults to 'bearer'."""
    from rest_assured.src.schemas.auth import TokenPair

    obj = TokenPair(access_token="a", refresh_token="r")
    assert obj.access_token == "a"
    assert obj.refresh_token == "r"
    assert obj.token_type == "bearer"


def test_token_pair_dump_has_exact_keys():
    """AC9: Pydantic dump contains exactly {access_token, refresh_token, token_type}."""
    from rest_assured.src.schemas.auth import TokenPair

    obj = TokenPair(access_token="a", refresh_token="r")
    dumped = obj.model_dump()
    assert set(dumped.keys()) == {"access_token", "refresh_token", "token_type"}


# ----------------------------------------------------------------------
# RefreshRequest
# ----------------------------------------------------------------------


def test_refresh_request_missing_field_raises():
    """AC10: Missing refresh_token raises ValidationError."""
    from rest_assured.src.schemas.auth import RefreshRequest

    with pytest.raises(ValidationError):
        RefreshRequest()  # type: ignore[call-arg]


def test_refresh_request_constructs_with_token():
    """AC11: RefreshRequest(refresh_token='abc') succeeds."""
    from rest_assured.src.schemas.auth import RefreshRequest

    obj = RefreshRequest(refresh_token="abc")
    assert obj.refresh_token == "abc"


def test_refresh_request_rejects_oversized_token():
    from rest_assured.src.schemas.auth import RefreshRequest

    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="x" * 2049)


def test_refresh_request_accepts_2048_char_token():
    from rest_assured.src.schemas.auth import RefreshRequest

    payload = RefreshRequest(refresh_token="x" * 2048)
    assert len(payload.refresh_token) == 2048
