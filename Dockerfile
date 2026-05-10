# syntax=docker/dockerfile:1.7

# Pin to specific patch version. Update digest via: docker pull python:3.13.3-slim
ARG PYTHON_IMAGE=python:3.13.3-slim

FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build

ENV POETRY_VERSION=1.8.4 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Layer-cache: deps only
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction --no-ansi --sync

# ---- Runtime stage ----
FROM ${PYTHON_IMAGE} AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

# Bring deps from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# App sources
COPY --chown=app:app rest_assured/ rest_assured/
COPY --chown=app:app settings.toml.example settings.toml

USER app
EXPOSE 8000

# exec-form: SIGTERM is forwarded to uvicorn (graceful scheduler shutdown)
CMD ["sh", "-c", "python -m alembic -c rest_assured/src/alembic.ini upgrade heads && exec uvicorn rest_assured.src.main:app --host 0.0.0.0 --port 8000"]
