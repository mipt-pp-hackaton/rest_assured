"""Integration tests for T8 — AuthService.register / AuthService.refresh and
repositories.users.create_user / get_user_by_id.

Needs a real DB because we assert on the unique-email constraint at the DB
layer. If testcontainers isn't installed the module is skipped, but never
silently — pytest collects a SKIP entry.
"""

from __future__ import annotations

import pytest

pytest.importorskip("testcontainers")

from sqlalchemy import exc as sa_exc  # noqa: E402
from sqlmodel import select  # noqa: E402

from rest_assured.src.models.users import User  # noqa: E402

# ---------------------------------------------------------------------------
# repositories.users.create_user / get_user_by_id
# ---------------------------------------------------------------------------


async def test_create_user_persists_row_and_returns_populated_user(postgres_connection):
    """AC #1 — create_user inserts a row, returns User with populated id and
    the requested attributes."""
    from rest_assured.src.repositories.users import create_user

    user = await create_user(
        postgres_connection,
        email="a@example.com",
        password_hash="$2b$abcde",
        is_superuser=False,
    )

    assert isinstance(user, User)
    assert user.email == "a@example.com"
    assert user.password_hash == "$2b$abcde"
    assert user.id is not None
    assert user.is_active is True
    assert user.is_superuser is False


async def test_get_user_by_id_returns_row_after_create(postgres_connection):
    """AC #2 — get_user_by_id round-trips the row inserted by create_user."""
    from rest_assured.src.repositories.users import create_user, get_user_by_id

    created = await create_user(
        postgres_connection,
        email="round@example.com",
        password_hash="$2b$xyz",
    )
    assert created.id is not None

    fetched = await get_user_by_id(postgres_connection, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "round@example.com"
    assert fetched.password_hash == "$2b$xyz"


async def test_get_user_by_id_returns_none_for_missing(postgres_connection):
    """get_user_by_id returns None for an id with no matching row."""
    from rest_assured.src.repositories.users import get_user_by_id

    assert await get_user_by_id(postgres_connection, 9_999_999) is None


async def test_create_user_duplicate_email_raises_integrity_error(postgres_connection):
    """AC #3 — creating two users with the same email inside one session must
    surface an SQLAlchemy error (IntegrityError for the unique constraint)."""
    from rest_assured.src.repositories.users import create_user

    await create_user(
        postgres_connection,
        email="dup@example.com",
        password_hash="$2b$first",
    )
    # Force the first INSERT to hit the DB so the second one trips the unique
    # constraint and not just Python-level state.
    await postgres_connection.commit()

    with pytest.raises((sa_exc.IntegrityError, sa_exc.SQLAlchemyError)):
        await create_user(
            postgres_connection,
            email="dup@example.com",
            password_hash="$2b$second",
        )
        await postgres_connection.commit()

    await postgres_connection.rollback()


# ---------------------------------------------------------------------------
# AuthService.register
# ---------------------------------------------------------------------------


async def test_register_returns_user_with_hashed_password(postgres_connection):
    """AC #4 — register() hashes the plaintext password and returns the User."""
    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService
    from rest_assured.src.services.auth.passwords import verify_password

    svc = AuthService(postgres_connection)
    user = await svc.register(UserCreate(email="reg@example.com", password="abcdefgh"))

    assert isinstance(user, User)
    assert user.email == "reg@example.com"
    assert user.id is not None
    # Plaintext must NOT be stored.
    assert user.password_hash != "abcdefgh"
    # And the stored hash must verify against the original password.
    assert verify_password("abcdefgh", user.password_hash) is True


async def test_register_duplicate_email_raises_409(postgres_connection):
    """AC #5 — duplicate email -> HTTPException(409) and DB stays single-rowed."""
    from fastapi import HTTPException

    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService

    svc = AuthService(postgres_connection)
    await svc.register(UserCreate(email="dup2@example.com", password="abcdefgh"))

    with pytest.raises(HTTPException) as excinfo:
        await svc.register(UserCreate(email="dup2@example.com", password="abcdefgh"))

    assert excinfo.value.status_code == 409
    assert excinfo.value.detail == "Email already registered"

    # Verify DB has exactly one row for that email.
    await postgres_connection.rollback()
    result = await postgres_connection.exec(select(User).where(User.email == "dup2@example.com"))
    rows = result.all()
    assert len(rows) == 1


async def test_register_with_is_superuser_true_persists_flag(postgres_connection):
    """AC #6 — is_superuser=True in the schema must make it onto the row."""
    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService

    svc = AuthService(postgres_connection)
    user = await svc.register(
        UserCreate(email="admin@example.com", password="abcdefgh", is_superuser=True)
    )

    assert user.is_superuser is True


# ---------------------------------------------------------------------------
# AuthService.refresh
# ---------------------------------------------------------------------------


async def test_refresh_returns_token_pair_with_valid_access(postgres_connection):
    """AC #7 — refresh() returns a TokenPair whose access_token decodes back
    to the same user id and token_type=access."""
    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService
    from rest_assured.src.services.auth.jwt import create_refresh_token, decode_token

    svc = AuthService(postgres_connection)
    user = await svc.register(UserCreate(email="refresh@example.com", password="abcdefgh"))
    assert user.id is not None

    refresh_token = create_refresh_token(user.id)
    pair = await svc.refresh(refresh_token)

    # TokenPair shape.
    assert pair.access_token
    assert pair.refresh_token
    assert pair.token_type == "bearer"

    payload = decode_token(pair.access_token, expected_type="access")
    # decode_token returns either a pydantic model or dataclass — both expose .sub / .token_type.
    sub = getattr(payload, "sub", None) or payload["sub"]  # type: ignore[index]
    token_type = getattr(payload, "token_type", None) or payload["token_type"]  # type: ignore[index]
    assert sub == str(user.id)
    assert token_type == "access"


async def test_refresh_rejects_access_token(postgres_connection):
    """AC #8 — passing an access token to refresh() raises HTTPException(401)."""
    from fastapi import HTTPException

    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService
    from rest_assured.src.services.auth.jwt import create_access_token

    svc = AuthService(postgres_connection)
    user = await svc.register(UserCreate(email="acc@example.com", password="abcdefgh"))
    assert user.id is not None

    access_token = create_access_token(user.id)

    with pytest.raises(HTTPException) as excinfo:
        await svc.refresh(access_token)

    assert excinfo.value.status_code == 401


async def test_refresh_rejects_inactive_user(postgres_connection):
    """AC #9 — inactive user can't refresh tokens; 401 or 403 are both
    acceptable refusals, but the call MUST refuse."""
    from fastapi import HTTPException

    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService
    from rest_assured.src.services.auth.jwt import create_refresh_token

    svc = AuthService(postgres_connection)
    user = await svc.register(UserCreate(email="inactive@example.com", password="abcdefgh"))
    assert user.id is not None

    # Deactivate the user post-registration.
    user.is_active = False
    postgres_connection.add(user)
    await postgres_connection.commit()

    refresh_token = create_refresh_token(user.id)

    with pytest.raises(HTTPException) as excinfo:
        await svc.refresh(refresh_token)

    assert excinfo.value.status_code in (
        401,
        403,
    ), f"Expected 401 or 403 for inactive user, got {excinfo.value.status_code}"


async def test_refresh_rejects_deleted_user(postgres_connection):
    """AC #10 — refresh token whose sub points to a non-existent user -> 401."""
    from fastapi import HTTPException

    from rest_assured.src.services.auth import AuthService
    from rest_assured.src.services.auth.jwt import create_refresh_token

    svc = AuthService(postgres_connection)
    # Build a refresh token for a user id that was never persisted.
    refresh_token = create_refresh_token(12_345_678)

    with pytest.raises(HTTPException) as excinfo:
        await svc.refresh(refresh_token)

    assert excinfo.value.status_code == 401


async def test_authenticate_rejects_inactive_user(postgres_connection):
    """Inactive users must not authenticate even with correct credentials.

    The router translates `None` from authenticate() to a generic 401
    "Incorrect email or password"; this is intentional to avoid leaking
    account state (disabled vs nonexistent vs wrong password).
    """
    from rest_assured.src.schemas.users import UserCreate
    from rest_assured.src.services.auth import AuthService

    svc = AuthService(postgres_connection)
    user = await svc.register(UserCreate(email="inactive-auth@example.com", password="abcdefgh"))
    assert user.id is not None

    # Sanity: while active, authenticate succeeds.
    active_result = await svc.authenticate("inactive-auth@example.com", "abcdefgh")
    assert active_result is not None

    # Deactivate and re-check: must return None (not the User), exactly like
    # wrong credentials.
    user.is_active = False
    postgres_connection.add(user)
    await postgres_connection.commit()

    result = await svc.authenticate("inactive-auth@example.com", "abcdefgh")
    assert result is None
