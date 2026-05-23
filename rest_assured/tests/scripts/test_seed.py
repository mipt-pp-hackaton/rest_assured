"""RED-phase tests for Fix A — scripts/seed.py cleanup.

Issues being pinned:
1. Broken imports: ``rest_assured.src.auth.passwords`` and
   ``rest_assured.src.models.user`` do not exist; correct modules are
   ``rest_assured.src.services.auth.passwords`` and
   ``rest_assured.src.models.users``.
2. The ``User`` model field is ``password_hash``, not ``hashed_password``.
3. The admin password is currently hardcoded to ``"admin"``. It must be read
   from the ``SEED_ADMIN_PASSWORD`` env var, and the script must raise a
   clear ``RuntimeError`` (not silently fall back) when it's missing/empty.

To satisfy these tests, the developer will need to refactor ``seed.py`` to
expose user construction as a synchronous helper (``build_admin_user()``)
that can be tested without running the full async DB seed.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from rest_assured.src.services.auth.passwords import verify_password


# ---------------------------------------------------------------------------
# AC #1 — import smoke
# ---------------------------------------------------------------------------
def test_seed_module_importable() -> None:
    """The seed module must be importable; today this fails on ModuleNotFoundError."""
    module = importlib.import_module("rest_assured.src.scripts.seed")
    assert module is not None


def test_seed_module_exposes_build_admin_user() -> None:
    """The seed module must expose a ``build_admin_user`` callable.

    The dev needs to extract user construction out of the async ``seed()``
    coroutine so we can test it without a live DB session.
    """
    module = importlib.import_module("rest_assured.src.scripts.seed")
    assert hasattr(
        module, "build_admin_user"
    ), "seed.py must expose `build_admin_user()` so admin construction is testable"
    assert callable(module.build_admin_user)


# ---------------------------------------------------------------------------
# AC #2 — Password is read from env var; User has correct fields
# ---------------------------------------------------------------------------
def test_build_admin_user_uses_password_hash_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "supersecret123")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    user = module.build_admin_user()

    # Pin the correct field name — `password_hash`, NOT `hashed_password`.
    assert hasattr(user, "password_hash"), "User model field must be `password_hash`"
    assert isinstance(user.password_hash, str)
    assert user.password_hash != ""
    # bcrypt hashes start with $2 (e.g. $2a$, $2b$).
    assert user.password_hash.startswith(
        "$2"
    ), f"Expected a bcrypt hash, got: {user.password_hash[:10]!r}"


def test_build_admin_user_sets_email_and_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "supersecret123")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    user = module.build_admin_user()

    assert user.email == "admin@example.com"
    assert user.is_superuser is True


def test_build_admin_user_password_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    """The hash must verify against the env-supplied password."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "supersecret123")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    user = module.build_admin_user()

    assert verify_password("supersecret123", user.password_hash) is True


# ---------------------------------------------------------------------------
# AC #3 — Missing or empty env var must raise RuntimeError
# ---------------------------------------------------------------------------
def test_build_admin_user_raises_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    with pytest.raises(RuntimeError):
        module.build_admin_user()


def test_build_admin_user_raises_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    with pytest.raises(RuntimeError):
        module.build_admin_user()


# ---------------------------------------------------------------------------
# AC #4 — No silent fallback to the literal "admin" password
# ---------------------------------------------------------------------------
def test_build_admin_user_does_not_fall_back_to_admin_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a strong password is supplied, the result must NOT match the legacy "admin" literal.

    Guards against the dev leaving the old hardcoded default as a fallback.
    """
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "supersecret123")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    user = module.build_admin_user()

    assert (
        verify_password("admin", user.password_hash) is False
    ), "build_admin_user() must NOT fall back to the hardcoded 'admin' password"


# ---------------------------------------------------------------------------
# AC #5 — Improvement A: whitespace-only password is rejected
# ---------------------------------------------------------------------------
def test_build_admin_user_rejects_whitespace_only_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A password consisting purely of whitespace must be treated as empty.

    Current code uses `if not password:` which lets `"   "` through. The fix
    is to strip the value before evaluating truthiness.
    """
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "   ")
    module = importlib.import_module("rest_assured.src.scripts.seed")
    importlib.reload(module)

    with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD"):
        module.build_admin_user()


# ---------------------------------------------------------------------------
# AC #6 — Improvement C: seed() uses session_scope, not manual try/finally
# ---------------------------------------------------------------------------
def test_seed_uses_session_scope_not_manual_try_finally() -> None:
    """Structural assertion: seed.py should use the canonical session_scope
    helper from repositories.database_session instead of a manual
    get_session() + try/finally + session.close() pattern.
    """
    src_path = Path(__file__).parent.parent.parent / "src" / "scripts" / "seed.py"
    source = src_path.read_text()
    assert (
        "session_scope" in source
    ), "seed.py should use session_scope helper from database_session.py"
    # Reject the old manual lifecycle pattern.
    assert (
        "await session.close()" not in source
    ), "seed.py should not manage session lifecycle manually — use session_scope"
