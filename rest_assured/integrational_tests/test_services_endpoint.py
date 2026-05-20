import pytest

_SERVICES_URL = "/api/services/"


# ---------------------------------------------------------------------------
# GET /api/services/
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_empty(async_client):
    response = await async_client.get(_SERVICES_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_returns_all(async_client, seed_service):
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
async def test_get_existing(async_client, seed_service):
    service = await seed_service(name="detail-svc")

    response = await async_client.get(f"{_SERVICES_URL}{service.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == service.id
    assert data["name"] == "detail-svc"


@pytest.mark.asyncio
async def test_get_not_found(async_client):
    response = await async_client.get(f"{_SERVICES_URL}99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/services/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_unauthorized(async_client, seed_service):
    service = await seed_service()
    response = await async_client.patch(
        f"{_SERVICES_URL}{service.id}", json={"name": "hacked"}
    )
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
