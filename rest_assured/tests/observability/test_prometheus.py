"""Unit-тесты Prometheus-экспозиции метрик."""

from datetime import datetime, timezone
from types import SimpleNamespace

from prometheus_client import generate_latest

from rest_assured.src.observability.prometheus import Observability, _SchedulerCollector


def _fake_runner(*, total=0, failed=0, workers=0, last_loop=None):
    return SimpleNamespace(
        checks_total=total,
        checks_failed=failed,
        active_workers_count=workers,
        last_loop_at=last_loop,
    )


def test_collector_yields_scheduler_metrics():
    runner = _fake_runner(total=10, failed=3, workers=2)
    families = {m.name: m for m in _SchedulerCollector(runner).collect()}

    # CounterMetricFamily хранит имя без суффикса _total
    assert families["rest_assured_checks"].samples[0].value == 10
    assert families["rest_assured_checks_failed"].samples[0].value == 3
    assert families["rest_assured_active_workers"].samples[0].value == 2


def test_last_loop_timestamp_zero_when_never_ran():
    runner = _fake_runner()
    families = {m.name: m for m in _SchedulerCollector(runner).collect()}
    assert families["rest_assured_scheduler_last_loop_timestamp_seconds"].samples[0].value == 0.0


def test_last_loop_timestamp_reflects_runner():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    runner = _fake_runner(last_loop=ts)
    families = {m.name: m for m in _SchedulerCollector(runner).collect()}
    sample = families["rest_assured_scheduler_last_loop_timestamp_seconds"].samples[0]
    assert sample.value == ts.timestamp()


def test_registry_renders_expected_metric_names():
    obs = Observability(_fake_runner(total=5, failed=1, workers=1))
    text = generate_latest(obs.registry).decode()

    assert "rest_assured_checks_total 5.0" in text
    assert "rest_assured_checks_failed_total 1.0" in text
    assert "rest_assured_active_workers 1.0" in text
    assert "rest_assured_scheduler_last_loop_timestamp_seconds" in text
    # HTTP-метрики зарегистрированы (значения появятся после первых запросов)
    assert "rest_assured_http_request_duration_seconds" in text


def test_two_instances_use_independent_registries():
    """Повторный create_app() не должен падать на дубле метрик в глобальном REGISTRY."""
    obs1 = Observability(_fake_runner())
    obs2 = Observability(_fake_runner())
    assert obs1.registry is not obs2.registry
