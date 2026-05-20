from datetime import timedelta

import pytest

from rest_assured.src.services.auth.jwt import create_access_token


@pytest.mark.asyncio
async def test_login_success(async_client, seed_user):
    await seed_user("user@example.com", "secret123")

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "secret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, seed_user):
    await seed_user("user@example.com", "correct_password")

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "wrong_password"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(async_client):
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "nonexistent@example.com", "password": "any"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "form",
    [
        {},  # ни username, ни password
        {"username": "u@example.com"},  # password отсутствует
        {"password": "secret"},  # username отсутствует
    ],
)
async def test_login_returns_422_on_malformed_form(async_client, form):
    """OAuth2PasswordRequestForm требует оба поля — иначе 422."""
    response = await async_client.post("/api/auth/login", data=form)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_me_with_valid_token(async_client, seed_user):
    await seed_user("admin@example.com", "pass123", is_admin=True)

    login_resp = await async_client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]

    me_resp = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "admin@example.com"
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_me_regular_user_is_admin_false(async_client, seed_user):
    await seed_user("regular@example.com", "pass123", is_admin=False)

    login_resp = await async_client.post(
        "/api/auth/login",
        data={"username": "regular@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    me_resp = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert me_resp.status_code == 200
    assert me_resp.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_me_without_token(async_client):
    response = await async_client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(async_client):
    response = await async_client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not_a_valid_jwt_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token(async_client, seed_user):
    await seed_user("user@example.com", "pass123")
    expired_token = create_access_token("user@example.com", expires_delta=timedelta(seconds=-1))

    response = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_authorized_client(authorized_client):
    """authorized_client уже несёт валидный JWT — защищённый эндпоинт отвечает 200."""
    response = await authorized_client.get("/api/incidents")
    assert response.status_code == 200
