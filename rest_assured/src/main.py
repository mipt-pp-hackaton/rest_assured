"""Точка входа FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from rest_assured.src.api.misc import misc_router
from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner
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

    @app.get("/api/health/scheduler")
    async def health_scheduler(request: Request):
        """Эндпоинт здоровья планировщика (T2.10)."""
        return request.app.state.runner.stats

    return app


app = create_app()
