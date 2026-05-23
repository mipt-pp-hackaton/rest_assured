import pytest
import pytest_asyncio
from sqlalchemy import update

from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import create_access_token, create_refresh_token

_SERVICES_URL = "/api/services/"


# ---------------------------------------------------------------------------
# T10 — router-level auth on /api/services
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def inactive_user_token(seed_user, postgres_connection) -> str:
    """Сидит юзера, потом флипает is_active=False — возвращает access token."""
    user = await seed_user("inactive-services@example.com", "secret123")
    token = create_access_token(user.id)
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()
    return token


@pytest_asyncio.fixture
async def refresh_token_for_active_user(seed_user) -> str:
    """Refresh token валидного юзера — должен отвергаться access-only эндпоинтами."""
    user = await seed_user("refresh-services@example.com", "secret123")
    return create_refresh_token(user.id)


@pytest.mark.asyncio
async def test_list_services_requires_auth(async_client):
    """T10 RED: GET /api/services/ без токена → 401."""
    response = await async_client.get(_SERVICES_URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_service_requires_auth(async_client, seed_service):
    """T10 RED: GET /api/services/{id} без токена → 401."""
    service = await seed_service()
    response = await async_client.get(f"{_SERVICES_URL}{service.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_services_with_active_token_returns_200(authorized_client, seed_service):
    """T10 GREEN-side: активный юзер + валидный access token → 200."""
    await seed_service(name="visible")
    response = await authorized_client.get(_SERVICES_URL)
    assert response.status_code == 200
    assert {s["name"] for s in response.json()} == {"visible"}


@pytest.mark.asyncio
async def test_create_service_with_active_token_returns_201(authorized_client):
    """T10 GREEN-side: активный юзер + валидный access token → 201."""
    response = await authorized_client.post(
        _SERVICES_URL,
        json={"name": "via-jwt", "url": "http://example.com"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "via-jwt"


@pytest.mark.asyncio
async def test_list_services_inactive_user_returns_403(async_client, inactive_user_token):
    """T10 RED: is_active=False → 403 'Inactive user'."""
    response = await async_client.get(
        _SERVICES_URL, headers={"Authorization": f"Bearer {inactive_user_token}"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_create_service_inactive_user_returns_403(async_client, inactive_user_token):
    """T10 RED: POST /api/services/ с токеном неактивного юзера → 403."""
    response = await async_client.post(
        _SERVICES_URL,
        json={"name": "x", "url": "http://example.com"},
        headers={"Authorization": f"Bearer {inactive_user_token}"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_delete_service_inactive_user_returns_403(
    async_client, inactive_user_token, seed_service
):
    """T10 RED: DELETE с токеном неактивного юзера → 403."""
    service = await seed_service()
    response = await async_client.delete(
        f"{_SERVICES_URL}{service.id}",
        headers={"Authorization": f"Bearer {inactive_user_token}"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_list_services_refresh_token_rejected(async_client, refresh_token_for_active_user):
    """T10 RED: refresh token вместо access → 401 'Invalid token type'."""
    response = await async_client.get(
        _SERVICES_URL,
        headers={"Authorization": f"Bearer {refresh_token_for_active_user}"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token type"}


# ---------------------------------------------------------------------------
# GET /api/services/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_empty(override_auth, async_client):
    response = await async_client.get(_SERVICES_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_returns_all(override_auth, async_client, seed_service):
    await seed_service(name="svc-a")
    await seed_service(name="svc-b")

    response = await async_client.get(_SERVICES_URL)
    assert response.status_code == 200
    assert {s["name"] for s in response.json()} == {"svc-a", "svc-b"}


# ---------------------------------------------------------------------------
# POST /api/services/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_unauthorized(async_client):
    response = await async_client.post(
        _SERVICES_URL, json={"name": "s", "url": "http://example.com"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create(override_auth, async_client):
    payload = {
        "name": "New Service",
        "url": "http://example.com",
        "http_method": "HEAD",
        "interval_ms": 5000,
        "expected_status": 200,
        "is_active": True,
    }
    response = await async_client.post(_SERVICES_URL, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Service"
    assert data["url"] == "http://example.com"
    assert data["http_method"] == "HEAD"
    assert data["interval_ms"] == 5000
    assert data["expected_status"] == 200
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_rejects_invalid_http_method(override_auth, async_client):
    response = await async_client.post(
        _SERVICES_URL,
        json={"name": "svc", "url": "http://example.com", "http_method": "FOO"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"url": "http://example.com"},  # missing name
        {"name": "svc"},  # missing url
        {},  # missing both
    ],
)
async def test_create_rejects_missing_required_fields(override_auth, async_client, payload):
    response = await async_client.post(_SERVICES_URL, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_existing(override_auth, async_client, seed_service):
    service = await seed_service(name="detail-svc")

    response = await async_client.get(f"{_SERVICES_URL}{service.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == service.id
    assert data["name"] == "detail-svc"


@pytest.mark.asyncio
async def test_get_not_found(override_auth, async_client):
    response = await async_client.get(f"{_SERVICES_URL}99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_unauthorized(async_client, seed_service):
    service = await seed_service()
    response = await async_client.patch(f"{_SERVICES_URL}{service.id}", json={"name": "hacked"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update(override_auth, async_client, seed_service):
    service = await seed_service(name="before")

    response = await async_client.patch(
        f"{_SERVICES_URL}{service.id}",
        json={"name": "after", "interval_ms": 10000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "after"
    assert data["interval_ms"] == 10000
    assert data["url"] == service.url  # нетронутые поля сохраняются


@pytest.mark.asyncio
async def test_update_not_found(override_auth, async_client):
    response = await async_client.patch(f"{_SERVICES_URL}99999", json={"name": "x"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_rejects_invalid_http_method(override_auth, async_client, seed_service):
    service = await seed_service()
    response = await async_client.patch(
        f"{_SERVICES_URL}{service.id}", json={"http_method": "WHATEVER"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_unauthorized(async_client, seed_service):
    service = await seed_service()
    response = await async_client.delete(f"{_SERVICES_URL}{service.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete(override_auth, async_client, seed_service):
    service = await seed_service()

    delete_response = await async_client.delete(f"{_SERVICES_URL}{service.id}")
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"{_SERVICES_URL}{service.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(override_auth, async_client):
    response = await async_client.delete(f"{_SERVICES_URL}99999")
    assert response.status_code == 404
