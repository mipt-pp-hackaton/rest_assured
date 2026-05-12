"""Интеграционные тесты модели CheckResult (T2.3)."""

import pytest
from sqlalchemy import text
from sqlmodel import select

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service


@pytest.mark.asyncio
async def test_check_result_round_trip(postgres_connection):
    s = Service(
        name="test-service",
        url="https://example.com",
        http_method="GET",
        interval_ms=1000,
    )
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    assert s.id is not None
    assert isinstance(s.id, int)

    cr = CheckResult(
        service_id=s.id,
        is_up=True,
        http_status=200,
        latency_ms=42,
    )
    postgres_connection.add(cr)
    await postgres_connection.commit()
    await postgres_connection.refresh(cr)

    assert cr.id is not None
    assert cr.service_id == s.id
    assert cr.is_up is True
    assert cr.http_status == 200
    assert cr.latency_ms == 42
    assert cr.error is None


@pytest.mark.asyncio
async def test_check_result_with_error(postgres_connection):
    s = Service(
        name="failing-service",
        url="https://fail.com",
        http_method="POST",
        interval_ms=5000,
    )
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    cr = CheckResult(
        service_id=s.id,
        is_up=False,
        http_status=None,
        latency_ms=5000,
        error="TimeoutException('Request timed out')",
    )
    postgres_connection.add(cr)
    await postgres_connection.commit()
    await postgres_connection.refresh(cr)

    assert cr.is_up is False
    assert cr.http_status is None
    assert "TimeoutException" in cr.error
    assert cr.latency_ms == 5000


@pytest.mark.asyncio
async def test_check_result_index_works(postgres_connection):
    result = await postgres_connection.exec(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'check_results' "
            "AND indexdef LIKE '%service_id%checked_at%'"
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1, "Индекс (service_id, checked_at) не найден"


@pytest.mark.asyncio
async def test_check_result_multiple_entries(postgres_connection):
    s = Service(
        name="multi-check",
        url="https://multi.com",
        http_method="HEAD",
        interval_ms=1000,
    )
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    for i in range(3):
        cr = CheckResult(
            service_id=s.id,
            is_up=i % 2 == 0,
            http_status=200 if i % 2 == 0 else 500,
            latency_ms=10 * (i + 1),
        )
        postgres_connection.add(cr)

    await postgres_connection.commit()

    result = await postgres_connection.exec(
        select(CheckResult).where(CheckResult.service_id == s.id)
    )
    checks = result.all()
    assert len(checks) == 3
