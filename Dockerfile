# syntax=docker/dockerfile:1.7

# Pin to specific patch version. Update digest via: docker pull python:3.13.3-slim
ARG PYTHON_IMAGE=python:3.13.3-slim

# ---- Build stage: install locked deps and build the rest_assured package ----
FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build

ENV POETRY_VERSION=2.3.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Layer-cache: locked runtime deps only (re-runs only when pyproject/lock change)
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Build the project wheel and install it on top of the locked deps. The wheel
# bundles the package code AND its data files (alembic migrations + alembic.ini,
# notification Jinja templates), so the runtime image needs no source tree.
# README.md is required by poetry-core because pyproject points [project].readme at it.
COPY README.md ./
COPY rest_assured/ rest_assured/
RUN poetry build --format wheel --no-interaction --no-ansi \
    && pip install --no-cache-dir --no-deps dist/*.whl

# ---- Runtime stage: run migrations, then serve ----
FROM ${PYTHON_IMAGE} AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

# Bring the installed deps, the rest_assured package and console scripts from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# settings.toml is resolved relative to the installed package
# (rest_assured/src/configs/app/main.py -> ../../../../settings.toml); for a
# site-packages install that root is the site-packages directory itself.
COPY --chown=app:app settings.toml /usr/local/lib/python3.13/site-packages/settings.toml

USER app
EXPOSE 8000

# exec-form server keeps SIGTERM forwarded to uvicorn (graceful scheduler shutdown).
# `pa-server migrate` resolves alembic.ini from inside the installed package.
CMD ["sh", "-c", "pa-server migrate && exec uvicorn rest_assured.src.main:app --host 0.0.0.0 --port 8000"]
