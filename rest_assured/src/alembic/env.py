"""Alembic environment configuration."""

import asyncio
import os
from alembic import context
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine

from rest_assured.src.configs.app.main import settings
from rest_assured.src.models import CheckResult, Service, Incident, NotificationLog, User  # noqa: F401

target_metadata = [Service.metadata,
    CheckResult.metadata,
    Incident.metadata,
    NotificationLog.metadata,]


def get_url():
    # 1. Из переменной окружения
    dsn = os.environ.get("DB_DSN")
    if dsn:
        return dsn
    # 2. Из конфига Alembic
    try:
        url = context.config.get_main_option("sqlalchemy.url")
        if url and url != "driver://user:pass@localhost/dbname":
            return url
    except AttributeError:
        pass
    # 3. Из настроек
    return settings.db_settings.dsl


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online(dsn: str | None = None):
    url = dsn or get_url()
    connectable = create_async_engine(url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


try:
    _ = context.config
    if context.config.config_file_name is not None:
        fileConfig(context.config.config_file_name)
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())
except AttributeError:
    pass
