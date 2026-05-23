from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import create_access_token, create_refresh_token


@pytest_asyncio.fixture
async def seed_three_incidents(seed_service, postgres_connection: AsyncSession) -> list[Incident]:
    """Сидит сервис и 3 инцидента: открытый, закрытый, SLA-breach (закрытый)."""
    service = await seed_service(name="svc1")

    now = datetime.now(timezone.utc)
    incidents = [
        Incident(
            service_id=service.id,
            opened_at=now - timedelta(hours=2),
            closed_at=None,
            sla_breach=False,
            last_error="err1",
        ),
        Incident(
            service_id=service.id,
            opened_at=now - timedelta(hours=5),
            closed_at=now - timedelta(hours=3),
            sla_breach=False,
            last_error="err2",
        ),
        Incident(
            service_id=service.id,
            opened_at=now - timedelta(hours=10),
            closed_at=now - timedelta(hours=8),
            sla_breach=True,
            last_error="err3",
        ),
    ]
    postgres_connection.add_all(incidents)
    await postgres_connection.commit()
    for inc in incidents:
        await postgres_connection.refresh(inc)
    return incidents


@pytest.mark.asyncio
async def test_unauthorized(async_client):
    response = await async_client.get("/api/incidents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_all(override_auth, async_client, seed_three_incidents):
    response = await async_client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Сортировка: первым идёт инцидент с самым свежим opened_at
    assert data[0]["opened_at"] > data[1]["opened_at"]


@pytest.mark.asyncio
async def test_filter_open_true(override_auth, async_client, seed_three_incidents):
    response = await async_client.get("/api/incidents?open=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["closed_at"] is None


@pytest.mark.asyncio
async def test_filter_open_false(override_auth, async_client, seed_three_incidents):
    """Граничный кейс: open=false вернёт только закрытые инциденты."""
    response = await async_client.get("/api/incidents?open=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["closed_at"] is not None for item in data)


@pytest.mark.asyncio
async def test_filter_service_and_open(override_auth, async_client, seed_three_incidents):
    service_id = seed_three_incidents[0].service_id

    response = await async_client.get(f"/api/incidents?service_id={service_id}&open=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service_id"] == service_id


@pytest.mark.asyncio
async def test_filter_sla_breach(override_auth, async_client, seed_three_incidents):
    response = await async_client.get("/api/incidents?sla_breach=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sla_breach"] is True


@pytest.mark.asyncio
async def test_duration_seconds(override_auth, async_client, seed_three_incidents):
    response = await async_client.get("/api/incidents")
    assert response.status_code == 200
    for inc in response.json():
        if inc["closed_at"] is None:
            assert inc["duration_seconds"] is None
        else:
            expected = int(
                (
                    datetime.fromisoformat(inc["closed_at"])
                    - datetime.fromisoformat(inc["opened_at"])
                ).total_seconds()
            )
            assert inc["duration_seconds"] == expected


@pytest.mark.asyncio
async def test_limit_caps_result_count(override_auth, async_client, seed_three_incidents):
    """Граница: limit=1 возвращает максимум 1 инцидент."""
    response = await async_client.get("/api/incidents?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1, 501, 1000])
async def test_limit_out_of_range_returns_422(override_auth, async_client, limit):
    """Граница: limit вне [1, 500] → 422 от FastAPI Query валидации."""
    response = await async_client.get(f"/api/incidents?limit={limit}")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# T11 — router-level auth on /api/incidents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_incidents_list_with_active_token_returns_200(authorized_client):
    """T11 GREEN-side: активный юзер + валидный access token → 200."""
    response = await authorized_client.get("/api/incidents")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_incidents_list_inactive_user_returns_403(
    async_client, seed_user, postgres_connection
):
    """T11 RED: is_active=False → 403 'Inactive user'."""
    user = await seed_user("inactive-incidents@example.com", "secret123")
    token = create_access_token(user.id)
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.get(
        "/api/incidents", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_incidents_list_refresh_token_rejected(async_client, seed_user):
    """T11 RED: refresh token вместо access → 401 'Invalid token type'."""
    user = await seed_user("refresh-incidents@example.com", "secret123")
    refresh = create_refresh_token(user.id)
    response = await async_client.get(
        "/api/incidents", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token type"}
