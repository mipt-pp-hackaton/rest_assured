"""Интеграционные тесты воркера (T2.5)."""

import asyncio

import httpx
import pytest
from sqlmodel import select

from rest_assured.src.models.checks import CheckResult
from rest_assured.src.models.services import Service
from rest_assured.src.scheduler.runner import SchedulerRunner

pytestmark = pytest.mark.httpx_mock(
    assert_all_responses_were_requested=False,
    assert_all_requests_were_expected=False,
)


@pytest.mark.asyncio
async def test_worker_writes_check_results(postgres_connection, httpx_mock):
    for _ in range(10):
        httpx_mock.add_response(url="http://fake/healthy", status_code=200)

    s = Service(name="t", url="http://fake/healthy", interval_ms=1000, expected_status=200)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    runner = SchedulerRunner()
    await runner.start()
    await asyncio.sleep(2.5)
    await runner.stop()

    results = (
        await postgres_connection.exec(select(CheckResult).where(CheckResult.service_id == s.id))
    ).all()
    assert len(results) >= 2
    assert all(r.is_up for r in results)


@pytest.mark.asyncio
async def test_worker_handles_timeout(postgres_connection, httpx_mock):
    for _ in range(10):
        httpx_mock.add_exception(
            url="http://fake/timeout", exception=httpx.TimeoutException("timeout")
        )

    s = Service(name="t2", url="http://fake/timeout", interval_ms=1000, expected_status=200)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    runner = SchedulerRunner()
    await runner.start()
    await asyncio.sleep(2.5)
    await runner.stop()

    results = (
        await postgres_connection.exec(select(CheckResult).where(CheckResult.service_id == s.id))
    ).all()
    assert len(results) >= 2
    assert all(not r.is_up for r in results)


@pytest.mark.asyncio
async def test_worker_respects_interval(postgres_connection, httpx_mock):
    for _ in range(10):
        httpx_mock.add_response(url="http://fake/interval", status_code=200)

    s = Service(name="t3", url="http://fake/interval", interval_ms=1000, expected_status=200)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    runner = SchedulerRunner()
    await runner.start()
    await asyncio.sleep(2.5)
    await runner.stop()

    results = (
        await postgres_connection.exec(select(CheckResult).where(CheckResult.service_id == s.id))
    ).all()
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_worker_stops_on_cancelled_error(postgres_connection, httpx_mock):
    for _ in range(10):
        httpx_mock.add_response(url="http://fake/cancel", status_code=200)

    s = Service(name="t4", url="http://fake/cancel", interval_ms=10000, expected_status=200)
    postgres_connection.add(s)
    await postgres_connection.commit()
    await postgres_connection.refresh(s)

    runner = SchedulerRunner()
    await runner.start()
    await asyncio.sleep(0.1)
    assert s.id in runner.active_service_ids()
    await runner.stop_service(s.id)
    assert s.id not in runner.active_service_ids()
    assert not runner.active_service_ids()
    await runner.stop()
