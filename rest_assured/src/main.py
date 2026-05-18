"""Точка входа FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from rest_assured.src.api.misc import misc_router
from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner

try:
    from rest_assured.src.api.auth import auth_router
except ImportError:
    auth_router = None

try:
    from rest_assured.src.api.services import services_router
except ImportError:
    services_router = None

from rest_assured.src.utils.version import get_app_version


def create_app() -> FastAPI:
    """Фабрика FastAPI приложения."""
    runner = SchedulerRunner()
    listener = ServiceChangeListener()
    listener.set_runner(runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Жизненный цикл приложения."""
        await runner.start()
        await listener.start()
        app.state.runner = runner
        app.state.listener = listener
        try:
            yield
        finally:
            await listener.stop()
            await runner.stop()

    app = FastAPI(
        title="rest-assured",
        version=get_app_version(),
        lifespan=lifespan,
    )

    app.include_router(misc_router)
    if auth_router:
        app.include_router(auth_router)
    if services_router:
        app.include_router(services_router)

    # Placeholder routers for other epics (connected here for visibility)
    # Epic 2: Scheduler — will be connected when ready
    # from rest_assured.src.api.scheduler import scheduler_router
    # app.include_router(scheduler_router)

    # Epic 3: Incidents — will be connected when ready
    # from rest_assured.src.api.incidents import incidents_router
    # app.include_router(incidents_router)

    # Epic 4: Notifications — will be connected when ready
    # from rest_assured.src.api.notifications import notifications_router
    # app.include_router(notifications_router)

    # Epic 5: Metrics — will be connected when ready
    # from rest_assured.src.api.metrics import metrics_router
    # app.include_router(metrics_router)

    @app.get("/api/health/scheduler")
    async def health_scheduler(request: Request):
        """Эндпоинт здоровья планировщика (T2.10)."""
        return request.app.state.runner.stats

    return app


app = create_app()
