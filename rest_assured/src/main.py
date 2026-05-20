"""Точка входа FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from rest_assured.src.api.misc import misc_router
from rest_assured.src.api.routers.auth import auth_router
from rest_assured.src.api.routers.incidents import router as incidents_router
from rest_assured.src.api.routers.metrics import router as metrics_router
from rest_assured.src.api.routers.scheduler import router as scheduler_router
from rest_assured.src.api.routers.services import router as services_router
from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.repositories.database_session import session_scope
from rest_assured.src.services.incidents import IncidentsService
from rest_assured.src.services.metrics_service import configure as configure_metrics_cache
from rest_assured.src.services.notifications.email import EmailSender
from rest_assured.src.services.scheduler.listener import ServiceChangeListener
from rest_assured.src.services.scheduler.runner import SchedulerRunner
from rest_assured.src.utils.version import get_app_version


def create_app() -> FastAPI:
    """Фабрика FastAPI приложения."""
    runner = SchedulerRunner()
    listener = ServiceChangeListener()
    listener.set_runner(runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        email_sender = EmailSender(settings.smtp)
        configure_metrics_cache(cache_ttl_seconds=settings.metrics.cache_ttl_seconds)

        app.state.email_sender = email_sender

        await runner.start()
        await listener.start()
        app.state.runner = runner
        app.state.listener = listener

        async def _check_result_callback(check: CheckResult) -> None:
            async with session_scope() as session:
                await IncidentsService(session).handle_check_result(
                    check,
                    email_sender=app.state.email_sender,
                    notifications_config=settings.notifications,
                )

        runner.register_callback(_check_result_callback)

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
    app.include_router(auth_router)
    app.include_router(incidents_router)
    app.include_router(metrics_router)
    app.include_router(scheduler_router)
    app.include_router(services_router)

    return app


app = create_app()
