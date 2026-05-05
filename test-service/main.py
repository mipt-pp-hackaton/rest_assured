"""Тестовый сервис с разными эндпоинтами для демонстрации."""

import random
import time

from fastapi import FastAPI, Query

app = FastAPI(title="Test Service for Rest Assured")

_controlled_down = False


@app.get("/healthy")
async def healthy():
    """Всегда отвечает 200."""
    return {"status": "ok"}


@app.get("/down")
async def down():
    """Всегда отвечает 500."""
    return {"status": "error"}, 500


@app.get("/flaky")
async def flaky():
    """Отвечает 200 или 500 случайно."""
    if random.random() < 0.5:
        return {"status": "ok"}
    return {"status": "error"}, 500


@app.get("/slow")
async def slow():
    """Отвечает с задержкой 3 секунды."""
    time.sleep(3)
    return {"status": "ok"}


@app.get("/controlled")
async def controlled():
    """Управляемый эндпоинт — возвращает 200 или 500."""
    if _controlled_down:
        return {"status": "error"}, 500
    return {"status": "ok"}


@app.get("/toggle")
async def toggle():
    """Переключает состояние /controlled."""
    global _controlled_down
    _controlled_down = not _controlled_down
    return {"controlled_down": _controlled_down}