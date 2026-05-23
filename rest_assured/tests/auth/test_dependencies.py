"""Unit tests for `get_current_active_user` and `get_current_superuser` (T7).

These tests verify the dependency-layer authorization predicates added on top
of `get_current_user`:

- ``get_current_active_user`` rejects users with ``is_active=False`` (403).
- ``get_current_superuser`` further rejects users without superuser flag (403).
- ``get_current_superuser`` is composed on top of ``get_current_active_user``,
  so an inactive superuser surfaces the "Inactive user" error first rather
  than "Not enough privileges".
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import Depends, HTTPException

from rest_assured.src.models.users import User
from rest_assured.src.services.auth.dependencies import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
)

# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------


async def test_active_user_passes_through() -> None:
    user = User(
        id=1,
        email="active@example.com",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )

    result = await get_current_active_user(current=user)

    assert result is user


async def test_inactive_user_rejected_with_403() -> None:
    user = User(
        id=2,
        email="inactive@example.com",
        password_hash="x",
        is_active=False,
        is_superuser=False,
    )

    with pytest.raises(HTTPException) as excinfo:
        await get_current_active_user(current=user)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Inactive user"


async def test_active_user_dependency_depends_on_get_current_user() -> None:
    """The `current` parameter must default to `Depends(get_current_user)` so
    FastAPI resolves the chain automatically."""
    sig = inspect.signature(get_current_active_user)
    param = sig.parameters["current"]
    default = param.default
    assert isinstance(default, type(Depends(get_current_user)))
    assert default.dependency is get_current_user


# ---------------------------------------------------------------------------
# get_current_superuser
# ---------------------------------------------------------------------------


async def test_superuser_passes_through_when_active_and_superuser() -> None:
    user = User(
        id=3,
        email="root@example.com",
        password_hash="x",
        is_active=True,
        is_superuser=True,
    )

    result = await get_current_superuser(current=user)

    assert result is user


async def test_non_superuser_rejected_with_403() -> None:
    user = User(
        id=4,
        email="mortal@example.com",
        password_hash="x",
        is_active=True,
        is_superuser=False,
    )

    with pytest.raises(HTTPException) as excinfo:
        await get_current_superuser(current=user)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Not enough privileges"


async def test_superuser_dependency_depends_on_active_user() -> None:
    """`get_current_superuser` MUST depend on `get_current_active_user`, so the
    inactive-user check fires before the superuser check (an inactive root
    sees "Inactive user", not "Not enough privileges")."""
    sig = inspect.signature(get_current_superuser)
    param = sig.parameters["current"]
    default = param.default
    assert isinstance(default, type(Depends(get_current_active_user)))
    assert default.dependency is get_current_active_user


async def test_inactive_superuser_sees_inactive_error_via_composition() -> None:
    """Compose the chain manually to confirm the surfaced error: an inactive
    superuser hitting the chain gets the 'Inactive user' 403 (because
    `get_current_superuser` depends on `get_current_active_user`)."""
    user = User(
        id=5,
        email="inactive-root@example.com",
        password_hash="x",
        is_active=False,
        is_superuser=True,
    )

    with pytest.raises(HTTPException) as excinfo:
        # Mirror what FastAPI's resolver does: first resolve the active-user
        # dep, then pass that to the superuser dep.
        active = await get_current_active_user(current=user)
        await get_current_superuser(current=active)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Inactive user"
