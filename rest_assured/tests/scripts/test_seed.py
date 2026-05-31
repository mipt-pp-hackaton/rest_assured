"""Unit tests for the demo/seed contract.

DB-free: every collaborator (``session_scope``, ``AuthService``,
``CatalogService`` and the repository helpers used by ``ensure_superuser``)
is replaced with a recording fake, so nothing touches a real database.
"""

import inspect
from contextlib import asynccontextmanager

from rest_assured.src.models.users import User
from rest_assured.src.scripts import seed
from rest_assured.src.services.auth import service as auth_service
from rest_assured.src.services.auth.passwords import verify_password
from rest_assured.src.services.auth.service import AuthService


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeAuthService:
    """Records the single ensure_superuser call."""

    calls: list[tuple[str, str]] = []

    def __init__(self, session):
        self.session = session

    async def ensure_superuser(self, email, password):
        type(self).calls.append((email, password))
        return User(id=1, email=email, password_hash="x", is_superuser=True)


class _FakeCatalogService:
    """Records created services; list_all returns a configurable set."""

    created: list[object] = []
    existing: list[object] = []

    def __init__(self, session):
        self.session = session

    async def list_all(self):
        return list(type(self).existing)

    async def create(self, data):
        type(self).created.append(data)
        return data


class _Existing:
    def __init__(self, url):
        self.url = url


@asynccontextmanager
async def _fake_session_scope():
    yield object()


def _patch_seed(monkeypatch, *, existing):
    """Wire the seed module to DB-free fakes and reset recorders."""
    _FakeAuthService.calls = []
    _FakeCatalogService.created = []
    _FakeCatalogService.existing = existing
    monkeypatch.setattr(seed, "session_scope", _fake_session_scope)
    monkeypatch.setattr(seed, "AuthService", _FakeAuthService)
    monkeypatch.setattr(seed, "CatalogService", _FakeCatalogService)


# --------------------------------------------------------------------------- #
# 1. Contract constants
# --------------------------------------------------------------------------- #
def test_admin_credentials_constants():
    assert seed.ADMIN_EMAIL == "admin@admin.com"
    assert seed.ADMIN_PASSWORD == "admin"


def test_demo_services_present():
    assert len(seed.DEMO_SERVICES) >= 2


def test_old_contract_symbol_removed():
    assert not hasattr(seed, "build_admin_user")


def test_seed_source_has_no_legacy_strings():
    src = inspect.getsource(seed)
    assert "SEED_ADMIN_PASSWORD" not in src
    assert "admin@example.com" not in src


# --------------------------------------------------------------------------- #
# 2. Service-layer composition (empty catalog -> create every demo)
# --------------------------------------------------------------------------- #
async def test_seed_creates_all_demo_services_when_empty(monkeypatch):
    _patch_seed(monkeypatch, existing=[])

    await seed.seed()

    assert _FakeAuthService.calls == [("admin@admin.com", "admin")]
    created_urls = {data.url for data in _FakeCatalogService.created}
    assert created_urls == {d.url for d in seed.DEMO_SERVICES}


async def test_seed_calls_ensure_superuser_exactly_once(monkeypatch):
    _patch_seed(monkeypatch, existing=[])

    await seed.seed()

    assert len(_FakeAuthService.calls) == 1


# --------------------------------------------------------------------------- #
# 3. Idempotent demo dedup (all urls already present -> zero creates)
# --------------------------------------------------------------------------- #
async def test_seed_is_idempotent_for_demo_services(monkeypatch):
    existing = [_Existing(d.url) for d in seed.DEMO_SERVICES]
    _patch_seed(monkeypatch, existing=existing)

    await seed.seed()

    assert _FakeCatalogService.created == []
    # admin step still runs even when nothing is created
    assert _FakeAuthService.calls == [("admin@admin.com", "admin")]


# --------------------------------------------------------------------------- #
# 4. AuthService.ensure_superuser happy path (creates a new superuser)
# --------------------------------------------------------------------------- #
async def test_ensure_superuser_creates_active_superuser(monkeypatch):
    recorded = {}

    async def _no_user(session, email):
        return None

    async def _fake_create_user(session, *, email, password_hash, is_superuser=False, **kw):
        recorded["email"] = email
        recorded["password_hash"] = password_hash
        return User(
            id=1,
            email=email,
            password_hash=password_hash,
            is_superuser=is_superuser,
        )

    monkeypatch.setattr(auth_service, "get_user_by_email", _no_user)
    monkeypatch.setattr(auth_service, "create_user", _fake_create_user)

    svc = AuthService(session=object())
    user = await svc.ensure_superuser("admin@admin.com", "admin")

    assert user.is_superuser is True
    assert user.is_active is True

    stored_hash = recorded["password_hash"]
    assert stored_hash.startswith("$2")
    assert verify_password("admin", stored_hash) is True
    assert verify_password("wrong", stored_hash) is False


# --------------------------------------------------------------------------- #
# 5. AuthService.ensure_superuser idempotent branch (user already exists)
# --------------------------------------------------------------------------- #
async def test_ensure_superuser_returns_existing_without_create(monkeypatch):
    existing_user = User(
        id=42,
        email="admin@admin.com",
        password_hash="$2b$preexisting",
        is_superuser=True,
    )

    async def _found(session, email):
        return existing_user

    async def _must_not_run(*args, **kwargs):
        raise AssertionError("create_user must not be called when user exists")

    monkeypatch.setattr(auth_service, "get_user_by_email", _found)
    monkeypatch.setattr(auth_service, "create_user", _must_not_run)

    svc = AuthService(session=object())
    user = await svc.ensure_superuser("admin@admin.com", "admin")

    assert user is existing_user


# --------------------------------------------------------------------------- #
# 6. Structural expectations on the seed source
# --------------------------------------------------------------------------- #
def test_seed_source_uses_expected_collaborators():
    src = inspect.getsource(seed)
    assert "session_scope" in src
    assert "AuthService" in src
    assert "CatalogService" in src


def test_seed_source_does_not_manually_close_session():
    src = inspect.getsource(seed)
    assert "await session.close()" not in src
