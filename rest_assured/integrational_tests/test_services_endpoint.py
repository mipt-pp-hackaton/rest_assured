import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.main import app
from rest_assured.src.models.services import Service

_BASE_URL = "http://test"
_SERVICES_URL = "/api/services/"


async def _seed_service(session: AsyncSession, **kwargs) -> Service:
    defaults = {"name": "Test Service", "url": "http://example.com", "interval_ms": 60000}
    defaults.update(kwargs)
    service = Service(**defaults)
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


# ---------------------------------------------------------------------------
# GET /api/services/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_empty(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.get(_SERVICES_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_returns_all(postgres_connection):
    await _seed_service(postgres_connection, name="svc-a")
    await _seed_service(postgres_connection, name="svc-b")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.get(_SERVICES_URL)
    assert response.status_code == 200
    names = {s["name"] for s in response.json()}
    assert names == {"svc-a", "svc-b"}


# ---------------------------------------------------------------------------
# POST /api/services/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_unauthorized(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.post(
            _SERVICES_URL, json={"name": "s", "url": "http://example.com"}
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create(override_auth, postgres_connection):
    payload = {
        "name": "New Service",
        "url": "http://example.com",
        "http_method": "HEAD",
        "interval_ms": 5000,
        "expected_status": 200,
        "is_active": True,
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.post(_SERVICES_URL, json=payload)

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


# ---------------------------------------------------------------------------
# GET /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_existing(postgres_connection):
    service = await _seed_service(postgres_connection, name="detail-svc")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.get(f"{_SERVICES_URL}{service.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == service.id
    assert data["name"] == "detail-svc"


@pytest.mark.asyncio
async def test_get_not_found(postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.get(f"{_SERVICES_URL}99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_unauthorized(postgres_connection):
    service = await _seed_service(postgres_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.patch(
            f"{_SERVICES_URL}{service.id}", json={"name": "hacked"}
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update(override_auth, postgres_connection):
    service = await _seed_service(postgres_connection, name="before")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.patch(
            f"{_SERVICES_URL}{service.id}",
            json={"name": "after", "interval_ms": 10000},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "after"
    assert data["interval_ms"] == 10000
    assert data["url"] == service.url  # нетронутые поля сохраняются


@pytest.mark.asyncio
async def test_update_not_found(override_auth, postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.patch(f"{_SERVICES_URL}99999", json={"name": "x"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_unauthorized(postgres_connection):
    service = await _seed_service(postgres_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.delete(f"{_SERVICES_URL}{service.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete(override_auth, postgres_connection):
    service = await _seed_service(postgres_connection)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        delete_response = await client.delete(f"{_SERVICES_URL}{service.id}")
        assert delete_response.status_code == 204

        get_response = await client.get(f"{_SERVICES_URL}{service.id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(override_auth, postgres_connection):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        response = await client.delete(f"{_SERVICES_URL}99999")
    assert response.status_code == 404
