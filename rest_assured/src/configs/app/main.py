"""Главный конфиг приложения."""

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings
from rest_assured.src.configs.app.smtp import SmtpConfig
from rest_assured.src.configs.app.notifications import NotificationsConfig


def _override_from_env(data: dict) -> dict:
    """Применяет переменные окружения с префиксом DYNACONF_ для переопределения настроек.

    Ожидается формат DYNACONF_SECTION__KEY=value, где SECTION и KEY – вложенные ключи.
    """
    prefix = "DYNACONF_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        # Убираем префикс
        config_key = key[len(prefix):].lower()
        # Разбиваем на секцию и ключ
        parts = config_key.split("__", maxsplit=1)
        if len(parts) != 2:
            continue
        section, setting = parts
        # Приводим к типу, пытаясь угадать int/bool/float/str
        if value.isdigit():
            value = int(value)
        elif value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.replace(".", "", 1).isdigit():
            value = float(value)
        # Устанавливаем в data
        data.setdefault(section, {})[setting] = value
    return data


class Settings(BaseModel):
    db_settings: DBConfig
    app_settings: APPConfig
    scheduler: SchedulerSettings
    smtp: SmtpConfig
    notifications: NotificationsConfig

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).parent.parent.parent.parent.parent
        toml_path = root / "settings.toml"
        if not toml_path.exists():
            raise FileNotFoundError(
                f"{toml_path} not found. "
                "Copy settings.toml.example to settings.toml and adjust values."
            )
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        # Переопределяем значения через переменные окружения (DYNACONF_*)
        data = _override_from_env(data)

        return cls(
            db_settings=DBConfig(**data["db_settings"]),
            app_settings=APPConfig(**data["app_settings"]),
            scheduler=SchedulerSettings(**data["scheduler"]),
            smtp=SmtpConfig(**data["smtp"]),
            notifications=NotificationsConfig(**data["notifications"]),
        )


settings = Settings.load()