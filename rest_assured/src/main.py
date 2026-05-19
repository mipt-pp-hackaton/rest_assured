"""Точка входа FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from rest_assured.src.api.misc import misc_router
from rest_assured.src.api.routers.incidents import router as incidents_router
from rest_assured.src.configs.app.main import settings
from rest_assured.src.models.checks import CheckResult
from rest_assured.src.notifications.email import EmailSender
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.scheduler.listener import ServiceChangeListener
from rest_assured.src.scheduler.runner import SchedulerRunner
from rest_assured.src.services.incidents import handle_check_result
from rest_assured.src.utils.version import get_app_version


def create_app() -> FastAPI:
    """Фабрика FastAPI приложения."""
    runner = SchedulerRunner()
    listener = ServiceChangeListener()
    listener.set_runner(runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Инициализация инфраструктуры
        email_sender = EmailSender(settings.smtp)
        # session_factory для передачи в callback (берём из проекта)
        session_factory = get_session
        metrics_service = None  # пока не реализован

        # Сохраняем в state, чтобы другие компоненты могли использовать
        app.state.email_sender = email_sender
        app.state.session_factory = session_factory
        app.state.metrics_service = metrics_service

        # Запускаем планировщик и слушатель
        await runner.start()
        await listener.start()
        app.state.runner = runner
        app.state.listener = listener

        # Регистрация callback'а обработки результатов проверок (T4.7)
        async def _check_result_callback(check: CheckResult) -> None:
            await handle_check_result(
                check,
                session_factory=app.state.session_factory,
                email_sender=app.state.email_sender,
                metrics_service=app.state.metrics_service,
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
    app.include_router(incidents_router)

    @app.get("/api/health/scheduler")
    async def health_scheduler(request: Request):
        """Эндпоинт здоровья планировщика (T2.10)."""
        return request.app.state.runner.stats

    return app


app = create_app()
