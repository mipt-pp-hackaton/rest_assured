from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.main import app
from rest_assured.src.models.incidents import Incident
from rest_assured.src.models.services import Service


async def _seed_incidents(session: AsyncSession) -> list[Incident]:
    service = Service(name="svc1", url="http://example.com", interval_ms=1000)
    session.add(service)
    await session.commit()
    await session.refresh(service)

    inc1 = Incident(
        service_id=service.id,
        opened_at=datetime.now(timezone.utc) - timedelta(hours=2),
        closed_at=None,
        sla_breach=False,
        last_error="err1",
    )
    inc2 = Incident(
        service_id=service.id,
        opened_at=datetime.now(timezone.utc) - timedelta(hours=5),
        closed_at=datetime.now(timezone.utc) - timedelta(hours=3),
        sla_breach=False,
        last_error="err2",
    )
    inc3 = Incident(
        service_id=service.id,
        opened_at=datetime.now(timezone.utc) - timedelta(hours=10),
        closed_at=datetime.now(timezone.utc) - timedelta(hours=8),
        sla_breach=True,
        last_error="err3",
    )
    session.add_all([inc1, inc2, inc3])
    await session.commit()
    return [inc1, inc2, inc3]


@pytest.mark.asyncio
async def test_unauthorized(postgres_connection):
    # Проверяем, что без JWT возвращается 401
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/incidents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_all(override_auth, postgres_connection):
    session = postgres_connection
    await _seed_incidents(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Проверка сортировки: первый в списке должен иметь самое позднее opened_at
    assert data[0]["opened_at"] > data[1]["opened_at"]


@pytest.mark.asyncio
async def test_filter_open(override_auth, postgres_connection):
    session = postgres_connection
    await _seed_incidents(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/incidents?open=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["closed_at"] is None


@pytest.mark.asyncio
async def test_filter_service_and_open(override_auth, postgres_connection):
    session = postgres_connection
    await _seed_incidents(session)
    # id сервиса мы знаем: это первый созданный, с id=1
    service_id = 1

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/incidents?service_id={service_id}&open=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service_id"] == service_id


@pytest.mark.asyncio
async def test_filter_sla_breach(override_auth, postgres_connection):
    session = postgres_connection
    await _seed_incidents(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/incidents?sla_breach=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sla_breach"] is True


@pytest.mark.asyncio
async def test_duration_seconds(override_auth, postgres_connection):
    session = postgres_connection
    await _seed_incidents(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    for inc in data:
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
