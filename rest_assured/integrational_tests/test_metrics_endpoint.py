from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.users import User
from rest_assured.src.services.auth.jwt import create_access_token, create_refresh_token

_BASE_URL = "http://test"


async def _seed_checks(
    session: AsyncSession,
    service_id: int,
    points: list[tuple[int, bool]],
    *,
    base: datetime,
    latency_ms: int | None = None,
) -> None:
    for seconds, is_up in points:
        session.add(
            CheckResult(
                service_id=service_id,
                checked_at=base + timedelta(seconds=seconds),
                is_up=is_up,
                http_status=200 if is_up else 500,
                latency_ms=latency_ms,
            )
        )
    await session.commit()


# ---------------------------------------------------------------------------
# GET /api/services/{id}/metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_returns_404_for_missing_service(override_auth, async_client):
    response = await async_client.get("/api/services/99999/metrics")
    assert response.status_code == 404
    assert response.json()["detail"] == "service not found"


@pytest.mark.asyncio
async def test_metrics_zero_for_service_without_checks(override_auth, async_client, seed_service):
    service = await seed_service()

    response = await async_client.get(f"/api/services/{service.id}/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["service_id"] == service.id
    assert data["current_uptime_seconds"] == 0
    assert data["sla_pct"] == 0.0
    assert datetime.fromisoformat(data["computed_at"]) <= datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_metrics_matches_sber_example(
    override_auth, async_client, seed_service, postgres_connection
):
    """SBER reference series: 7 checks, current uptime = 10s, SLA = 50%."""
    service = await seed_service()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await _seed_checks(
        postgres_connection,
        service.id,
        [(0, False), (10, True), (20, True), (30, True), (40, False), (50, True), (60, True)],
        base=base,
    )

    response = await async_client.get(f"/api/services/{service.id}/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["current_uptime_seconds"] == 10
    assert data["sla_pct"] == 50.0


# ---------------------------------------------------------------------------
# GET /api/services/summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_empty_when_no_services(override_auth, async_client):
    response = await async_client.get("/api/services/summary")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_summary_excludes_inactive_services(override_auth, async_client, seed_service):
    await seed_service(name="active", is_active=True)
    await seed_service(name="inactive", is_active=False)

    response = await async_client.get("/api/services/summary")

    assert response.status_code == 200
    names = [row["name"] for row in response.json()]
    assert names == ["active"]


@pytest.mark.asyncio
async def test_summary_reports_last_check_and_metrics(
    override_auth, async_client, seed_service, postgres_connection
):
    service = await seed_service()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await _seed_checks(
        postgres_connection,
        service.id,
        [(0, True), (10, True), (20, True)],
        base=base,
    )

    response = await async_client.get("/api/services/summary")

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["service_id"] == service.id
    assert row["current_uptime_seconds"] == 20
    assert row["sla_pct"] == 100.0
    assert row["last_check_is_up"] is True
    assert datetime.fromisoformat(row["last_check_at"]) == base + timedelta(seconds=20)


# ---------------------------------------------------------------------------
# GET /api/services/{id}/timeseries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeseries_returns_404_for_missing_service(override_auth, async_client):
    response = await async_client.get(
        "/api/services/99999/timeseries",
        params={"from": "2026-01-01T12:00:00Z", "to": "2026-01-01T13:00:00Z"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "service not found"


@pytest.mark.asyncio
async def test_timeseries_returns_422_when_to_not_after_from(
    override_auth, async_client, seed_service
):
    service = await seed_service()

    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={"from": "2026-01-01T12:00:00Z", "to": "2026-01-01T12:00:00Z"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_timeseries_empty_when_range_has_no_checks(
    override_auth, async_client, seed_service, postgres_connection
):
    service = await seed_service()
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    await _seed_checks(
        postgres_connection,
        service.id,
        [(0, True), (10, True)],
        base=base,
    )

    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={"from": "2026-01-01T13:00:00Z", "to": "2026-01-01T14:00:00Z"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_timeseries_groups_checks_into_buckets(
    override_auth, async_client, seed_service, postgres_connection
):
    service = await seed_service()
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # 60 all-up checks at 1s intervals → 6 buckets of 10s, 10 checks each
    points = [(i, True) for i in range(60)]
    await _seed_checks(postgres_connection, service.id, points, base=base, latency_ms=100)

    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={
            "from": "2026-01-01T12:00:00Z",
            "to": "2026-01-01T12:01:00Z",
            "bucket_seconds": 10,
        },
    )

    assert response.status_code == 200
    buckets = response.json()
    assert len(buckets) == 6
    expected_starts = [
        (base + timedelta(seconds=10 * i)).isoformat().replace("+00:00", "Z") for i in range(6)
    ]
    assert [b["bucket_start"] for b in buckets] == expected_starts
    for bucket in buckets:
        assert bucket["checks_total"] == 10
        assert bucket["checks_up"] == 10
        assert bucket["up_ratio"] == 1.0
        assert bucket["latency_avg_ms"] == 100.0
        assert bucket["latency_p95_ms"] == 100.0


@pytest.mark.asyncio
async def test_timeseries_counts_down_checks_per_bucket(
    override_auth, async_client, seed_service, postgres_connection
):
    service = await seed_service()
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # First bucket: 7 up + 3 down; second bucket: all up
    bucket_a = [(i, True) for i in range(7)] + [(i, False) for i in range(7, 10)]
    bucket_b = [(i, True) for i in range(10, 20)]
    await _seed_checks(postgres_connection, service.id, bucket_a + bucket_b, base=base)

    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={
            "from": "2026-01-01T12:00:00Z",
            "to": "2026-01-01T12:00:20Z",
            "bucket_seconds": 10,
        },
    )

    assert response.status_code == 200
    buckets = response.json()
    assert len(buckets) == 2
    assert buckets[0]["checks_total"] == 10
    assert buckets[0]["checks_up"] == 7
    assert buckets[0]["up_ratio"] == 0.7
    assert buckets[1]["checks_up"] == 10
    assert buckets[1]["up_ratio"] == 1.0


@pytest.mark.asyncio
async def test_timeseries_computes_p95_latency(
    override_auth, async_client, seed_service, postgres_connection
):
    service = await seed_service()
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # 10 checks with latency_ms = 0..9
    for i in range(10):
        postgres_connection.add(
            CheckResult(
                service_id=service.id,
                checked_at=base + timedelta(seconds=i),
                is_up=True,
                http_status=200,
                latency_ms=i,
            )
        )
    await postgres_connection.commit()

    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={
            "from": "2026-01-01T12:00:00Z",
            "to": "2026-01-01T12:00:10Z",
            "bucket_seconds": 10,
        },
    )

    assert response.status_code == 200
    buckets = response.json()
    assert len(buckets) == 1
    bucket = buckets[0]
    assert bucket["checks_total"] == 10
    # percentile_cont(0.95) over [0..9] = 8.55
    assert bucket["latency_p95_ms"] == pytest.approx(8.55)


# ---------------------------------------------------------------------------
# T12 — router-level auth on /api/services (metrics endpoints)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_requires_auth(async_client):
    """T12 RED: GET /api/services/summary без токена → 401."""
    response = await async_client.get("/api/services/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_service_metrics_requires_auth(async_client, seed_service):
    """T12 RED: GET /api/services/{id}/metrics без токена → 401."""
    service = await seed_service()
    response = await async_client.get(f"/api/services/{service.id}/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_service_timeseries_requires_auth(async_client, seed_service):
    """T12 RED: GET /api/services/{id}/timeseries без токена → 401."""
    service = await seed_service()
    response = await async_client.get(
        f"/api/services/{service.id}/timeseries",
        params={"from": "2026-01-01T12:00:00Z", "to": "2026-01-01T13:00:00Z"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_summary_with_active_token_returns_200(authorized_client):
    """T12 GREEN-side: активный юзер → 200."""
    response = await authorized_client.get("/api/services/summary")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_summary_inactive_user_returns_403(async_client, seed_user, postgres_connection):
    """T12 RED: is_active=False → 403 'Inactive user'."""
    user = await seed_user("inactive-metrics@example.com", "secret123")
    token = create_access_token(user.id)
    await postgres_connection.exec(update(User).where(User.id == user.id).values(is_active=False))
    await postgres_connection.commit()

    response = await async_client.get(
        "/api/services/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


@pytest.mark.asyncio
async def test_summary_refresh_token_rejected(async_client, seed_user):
    """T12 RED: refresh token вместо access → 401 'Invalid token type'."""
    user = await seed_user("refresh-metrics@example.com", "secret123")
    refresh = create_refresh_token(user.id)
    response = await async_client.get(
        "/api/services/summary", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token type"}
