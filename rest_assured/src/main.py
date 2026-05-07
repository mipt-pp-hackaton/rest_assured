"""Точка входа FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from rest_assured.src.api.misc import misc_router
from rest_assured.src.scheduler.runner import scheduler_runner
from rest_assured.src.scheduler.listener import ServiceChangeListener

listener = ServiceChangeListener()
listener.set_runner(scheduler_runner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    await scheduler_runner.start()
    await listener.start()
    yield
    await listener.stop()
    await scheduler_runner.stop()


app = FastAPI(
    title="Rest Assured",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(misc_router)


@app.get("/api/health/scheduler")
async def health_scheduler():
    """Эндпоинт здоровья планировщика (T2.10)."""
    return scheduler_runner.stats
