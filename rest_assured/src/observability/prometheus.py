"""Prometheus-метрики приложения.

Экспортирует на ``GET /metrics`` две группы метрик:

* **доменные метрики планировщика** ("мониторинг мониторинга") — читаются прямо
  из живых счётчиков :class:`SchedulerRunner` в момент scrape'а, поэтому
  источник истины один и тот же, что и у ``GET /api/health/scheduler``;
* **HTTP-метрики API** — счётчик запросов и гистограмма латентности, которые
  наполняет middleware (см. :meth:`Observability.instrument`).

Каждый экземпляр приложения держит собственный :class:`CollectorRegistry`
(не глобальный ``REGISTRY``), поэтому повторный ``create_app()`` в тестах не
приводит к ошибке "Duplicated timeseries".
"""

from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING, Iterator

from prometheus_client import CollectorRegistry, Counter, Histogram, make_asgi_app
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

if TYPE_CHECKING:
    from fastapi import FastAPI

    from rest_assured.src.services.scheduler.runner import SchedulerRunner


class _SchedulerCollector:
    """Лениво отдаёт счётчики раннера на момент scrape'а (single source of truth)."""

    def __init__(self, runner: "SchedulerRunner") -> None:
        self._runner = runner

    def describe(self) -> list:
        # Пустой describe() говорит registry не вызывать collect() при регистрации
        # (иначе дубль-проверка имён трогала бы раннер слишком рано).
        return []

    def collect(self) -> Iterator:
        runner = self._runner

        checks_total = CounterMetricFamily(
            "rest_assured_checks",
            "Total number of service checks executed by the scheduler.",
        )
        checks_total.add_metric([], float(runner.checks_total))
        yield checks_total

        checks_failed = CounterMetricFamily(
            "rest_assured_checks_failed",
            "Total number of service checks that resulted in a DOWN verdict.",
        )
        checks_failed.add_metric([], float(runner.checks_failed))
        yield checks_failed

        active_workers = GaugeMetricFamily(
            "rest_assured_active_workers",
            "Number of per-service scheduler worker tasks currently running.",
        )
        active_workers.add_metric([], float(runner.active_workers_count))
        yield active_workers

        last_loop = GaugeMetricFamily(
            "rest_assured_scheduler_last_loop_timestamp_seconds",
            "Unix timestamp of the most recent completed check loop (0 if none yet).",
        )
        ts = runner.last_loop_at.timestamp() if runner.last_loop_at is not None else 0.0
        last_loop.add_metric([], ts)
        yield last_loop


class Observability:
    """Собирает реестр метрик и подключает его к FastAPI-приложению."""

    def __init__(self, runner: "SchedulerRunner") -> None:
        self.registry = CollectorRegistry()
        self.registry.register(_SchedulerCollector(runner))

        self.http_requests = Counter(
            "rest_assured_http_requests",
            "Total HTTP requests handled by the API.",
            ["method", "status"],
            registry=self.registry,
        )
        self.http_latency = Histogram(
            "rest_assured_http_request_duration_seconds",
            "HTTP request latency in seconds.",
            ["method"],
            registry=self.registry,
        )
        self.asgi_app = make_asgi_app(registry=self.registry)

    def instrument(self, app: "FastAPI") -> None:
        """Смонтировать ``/metrics`` и навесить middleware учёта HTTP-запросов."""
        app.mount("/metrics", self.asgi_app)

        @app.middleware("http")
        async def _record_http_metrics(request, call_next):
            # Не учитываем сам scrape метрик, чтобы не зашумлять статистику.
            if request.url.path.startswith("/metrics"):
                return await call_next(request)

            start = monotonic()
            response = await call_next(request)
            elapsed = monotonic() - start

            self.http_latency.labels(method=request.method).observe(elapsed)
            self.http_requests.labels(
                method=request.method,
                status=str(response.status_code),
            ).inc()
            return response
