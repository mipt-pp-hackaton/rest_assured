from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.main import app
from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import create_access_token
from rest_assured.src.services.auth.passwords import hash_password


async def _create_user(
    session: AsyncSession,
    email: str,
    password: str,
    is_admin: bool = False,
) -> User:
    user = User(email=email, password_hash=hash_password(password), is_admin=is_admin)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success(postgres_connection):
    await _create_user(postgres_connection, "user@example.com", "secret123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            data={"username": "user@example.com", "password": "secret123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(postgres_connection):
    await _create_user(postgres_connection, "user@example.com", "correct_password")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            data={"username": "user@example.com", "password": "wrong_password"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            data={"username": "nonexistent@example.com", "password": "any"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(postgres_connection):
    await _create_user(postgres_connection, "admin@example.com", "pass123", is_admin=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": "admin@example.com", "password": "pass123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "admin@example.com"
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_me_regular_user_is_admin_false(postgres_connection):
    await _create_user(postgres_connection, "regular@example.com", "pass123", is_admin=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": "regular@example.com", "password": "pass123"},
        )
        token = login_resp.json()["access_token"]
        me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    assert me_resp.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_me_without_token(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not_a_valid_jwt_token"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token(postgres_connection):
    await _create_user(postgres_connection, "user@example.com", "pass123")
    expired_token = create_access_token("user@example.com", expires_delta=timedelta(seconds=-1))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_real_jwt(postgres_connection):
    await _create_user(postgres_connection, "user@example.com", "pass123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": "user@example.com", "password": "pass123"},
        )
        token = login_resp.json()["access_token"]

        incidents_resp = await client.get(
            "/api/incidents", headers={"Authorization": f"Bearer {token}"}
        )

    assert incidents_resp.status_code == 200
