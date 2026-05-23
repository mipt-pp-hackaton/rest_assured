from datetime import timedelta

import pytest
from sqlalchemy import update

from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

# ---------------------------------------------------------------------------
# POST /api/auth/login — now returns TokenPair (access + refresh)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(async_client, seed_user):
    """AC #1 (T9): login returns TokenPair shape — access + refresh + bearer.
    UPDATED from T6: previously asserted just `access_token` (Token); the new
    contract requires both tokens in a TokenPair.
    """
    await seed_user("user@example.com", "secret123")

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "secret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert isinstance(body["refresh_token"], str) and body["refresh_token"]


@pytest.mark.asyncio
async def test_login_access_token_has_correct_claims(async_client, seed_user):
    """AC #2: decoded access token has sub == str(user.id) and token_type=access."""
    user = await seed_user("claims-access@example.com", "secret123")
    assert user.id is not None

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "claims-access@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()

    payload = decode_token(body["access_token"], expected_type="access")
    assert payload.sub == str(user.id)
    assert payload.token_type == "access"


@pytest.mark.asyncio
async def test_login_refresh_token_has_correct_claims(async_client, seed_user):
    """AC #3: decoded refresh token has sub == str(user.id) and token_type=refresh."""
    user = await seed_user("claims-refresh@example.com", "secret123")
    assert user.id is not None

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "claims-refresh@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()

    payload = decode_token(body["refresh_token"], expected_type="refresh")
    assert payload.sub == str(user.id)
    assert payload.token_type == "refresh"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, seed_user):
    """AC #4: wrong password -> 401, generic message ('Incorrect email or password')."""
    await seed_user("user@example.com", "correct_password")

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


@pytest.mark.asyncio
async def test_login_unknown_user(async_client):
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "nonexistent@example.com", "password": "any"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401_generic(
    async_client, seed_user, postgres_connection
):
    """AC #5: inactive user with the correct password -> generic 401, not 403.
    AuthService.authenticate returns None for inactive users so we can't leak
    account state via the login response.
    """
    user = await seed_user("inactive-login@example.com", "secret123")

    # Deactivate user post-creation.
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.post(
        "/api/auth/login",
        data={"username": "inactive-login@example.com", "password": "secret123"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


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


# ---------------------------------------------------------------------------
# POST /api/auth/register — superuser-only registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_anonymous_returns_401(async_client):
    """AC #6: register requires authentication; no token -> 401."""
    response = await async_client.post(
        "/api/auth/register",
        json={"email": "anon@example.com", "password": "abcdefgh"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_non_superuser_returns_403(async_client, seed_user):
    """AC #7: authenticated but not-a-superuser -> 403 'Not enough privileges'."""
    regular = await seed_user("plain@example.com", "secret123", is_superuser=False)
    token = create_access_token(regular.id)

    response = await async_client.post(
        "/api/auth/register",
        json={"email": "newbie@example.com", "password": "abcdefgh"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough privileges"}


@pytest.mark.asyncio
async def test_register_superuser_creates_user_and_returns_userread(async_client, seed_user):
    """AC #8: authenticated superuser, valid body -> 201, body matches UserRead.
    UserRead fields: id, email, is_active, is_superuser, created_at, updated_at.
    NEVER returns `password_hash`.
    """
    admin = await seed_user("root@example.com", "secret123", is_superuser=True)
    token = create_access_token(admin.id)

    response = await async_client.post(
        "/api/auth/register",
        json={"email": "fresh@example.com", "password": "abcdefgh"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) >= {
        "id",
        "email",
        "is_active",
        "is_superuser",
        "created_at",
        "updated_at",
    }
    # CRITICAL: password_hash must never leak.
    assert "password_hash" not in body
    assert "password" not in body
    assert body["email"] == "fresh@example.com"
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert isinstance(body["id"], int)


@pytest.mark.asyncio
async def test_register_superuser_duplicate_email_returns_409(async_client, seed_user):
    """AC #9: duplicate email -> 409 'Email already registered'."""
    admin = await seed_user("root2@example.com", "secret123", is_superuser=True)
    token = create_access_token(admin.id)

    # First create.
    first = await async_client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "abcdefgh"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201

    # Second create with same email.
    second = await async_client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "anotherpass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "Email already registered"}


@pytest.mark.asyncio
async def test_register_superuser_short_password_returns_422(async_client, seed_user):
    """AC #10: body with password shorter than 8 chars -> 422 (Pydantic)."""
    admin = await seed_user("root3@example.com", "secret123", is_superuser=True)
    token = create_access_token(admin.id)

    response = await async_client.post(
        "/api/auth/register",
        json={"email": "shortpw@example.com", "password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_superuser_with_is_superuser_true_flag(async_client, seed_user):
    """AC #11: register a superuser sets is_superuser=true on the result."""
    admin = await seed_user("root4@example.com", "secret123", is_superuser=True)
    token = create_access_token(admin.id)

    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "admin2@example.com",
            "password": "abcdefgh",
            "is_superuser": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_superuser"] is True


# ---------------------------------------------------------------------------
# POST /api/auth/refresh — token rotation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_valid_token_returns_fresh_pair(async_client, seed_user):
    """AC #12: valid refresh token -> 200 with a fresh TokenPair."""
    user = await seed_user("refresh-ok@example.com", "secret123")
    refresh_token = create_refresh_token(user.id)

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"

    # The new access token must decode and reference the same user id.
    payload = decode_token(body["access_token"], expected_type="access")
    assert payload.sub == str(user.id)
    assert payload.token_type == "access"


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(async_client, seed_user):
    """AC #13: passing an access token (token_type=access) -> 401 'Invalid token type'."""
    user = await seed_user("acc-not-refresh@example.com", "secret123")
    access_token = create_access_token(user.id)

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token type"}


@pytest.mark.asyncio
async def test_refresh_with_expired_token_returns_401(async_client, seed_user):
    """AC #14: expired refresh token -> 401."""
    user = await seed_user("expired-refresh@example.com", "secret123")
    expired_refresh = create_refresh_token(user.id, ttl=timedelta(seconds=-1))

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": expired_refresh},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_tampered_signature_returns_401(async_client, seed_user):
    """AC #15: refresh token whose signature has been tampered -> 401."""
    user = await seed_user("tampered@example.com", "secret123")
    refresh_token = create_refresh_token(user.id)

    # Tamper with the signature segment (last segment after the last '.').
    parts = refresh_token.split(".")
    assert len(parts) == 3
    tampered = ".".join(parts[:2] + ["x" + parts[2][1:]])  # flip first signature char

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": tampered},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_for_deactivated_user_returns_403(
    async_client, seed_user, postgres_connection
):
    """AC #16: refresh for a user who's been deactivated since issuance -> 403
    'Inactive user'.
    """
    user = await seed_user("dead@example.com", "secret123")
    refresh_token = create_refresh_token(user.id)

    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_refresh_for_deleted_user_returns_401(async_client):
    """AC #17: refresh whose sub points to a non-existent user -> 401 generic."""
    refresh_token = create_refresh_token(99_999_999)

    response = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me — now uses get_current_active_user and response_model=UserRead
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_userread(async_client, seed_user):
    """AC #18: /me returns the UserRead schema (id, email, is_active,
    is_superuser, created_at, updated_at) — never password_hash.
    UPDATED from T6: previously asserted untyped dict {email, is_superuser}.
    """
    user = await seed_user("me-shape@example.com", "pass1234", is_superuser=True)

    login_resp = await async_client.post(
        "/api/auth/login",
        data={"username": "me-shape@example.com", "password": "pass1234"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    data = me_resp.json()
    assert set(data.keys()) >= {
        "id",
        "email",
        "is_active",
        "is_superuser",
        "created_at",
        "updated_at",
    }
    assert "password_hash" not in data
    assert data["id"] == user.id
    assert data["email"] == "me-shape@example.com"
    assert data["is_active"] is True
    assert data["is_superuser"] is True


@pytest.mark.asyncio
async def test_me_regular_user_is_superuser_false(async_client, seed_user):
    """Sanity: a regular user is_superuser=False through /me (UserRead)."""
    await seed_user("regular@example.com", "pass123", is_superuser=False)

    login_resp = await async_client.post(
        "/api/auth/login",
        data={"username": "regular@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    me_resp = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["is_superuser"] is False
    # Ensure UserRead-only fields are present (no password leakage).
    assert "password_hash" not in body
    assert "id" in body


@pytest.mark.asyncio
async def test_me_inactive_user_returns_403(async_client, seed_user, postgres_connection):
    """AC #19: an inactive user with a valid token on /me -> 403 'Inactive user'.
    /me must use get_current_active_user, not the bare get_current_user.
    """
    user = await seed_user("inactive-me@example.com", "secret123")
    token = create_access_token(user.id)

    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_me_without_token(async_client):
    """AC #20: anonymous /me -> 401."""
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
    user = await seed_user("user@example.com", "pass123")
    expired_token = create_access_token(user.id, ttl=timedelta(seconds=-1))

    response = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_authorized_client(authorized_client):
    """authorized_client уже несёт валидный JWT — защищённый эндпоинт отвечает 200."""
    response = await authorized_client.get("/api/incidents")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_to_me_cross_flow_uses_user_id_as_subject(async_client, seed_user):
    """Regression: login emits an access token whose `sub` is the user's id
    (as a string), and `/api/auth/me` accepts that token and returns the
    seeded user. Guards against the prior bug where login set
    ``sub=user.email`` while get_current_user resolved ``sub`` as ``user.id``.
    """
    seeded = await seed_user("cross@example.com", "secret123", is_superuser=True)
    assert seeded.id is not None

    login_resp = await async_client.post(
        "/api/auth/login",
        data={"username": "cross@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    payload = decode_token(access_token, expected_type="access")
    assert payload.sub == str(seeded.id)

    me_resp = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "cross@example.com"
    assert data["is_superuser"] is True


# ---------------------------------------------------------------------------
# Public endpoint sanity — tokenUrl + Swagger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oauth2_token_url_remains_login_endpoint():
    """AC #21: the OAuth2PasswordBearer tokenUrl is still '/api/auth/login' so
    Swagger 'Authorize' continues to work after the T9 refactor.
    """
    from rest_assured.src.services.auth import dependencies as deps

    assert deps._oauth2_scheme.model.flows.password.tokenUrl == "/api/auth/login"


@pytest.mark.asyncio
async def test_docs_endpoint_is_public(async_client):
    """AC #22a: /docs is reachable without auth."""
    response = await async_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json_is_public(async_client):
    """AC #22b: /openapi.json is reachable without auth."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert "paths" in body
    # Sanity: login is documented under the expected path.
    assert "/api/auth/login" in body["paths"]
