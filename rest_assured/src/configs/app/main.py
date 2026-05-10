"""Главный конфиг приложения."""

import tomllib
from pathlib import Path

from pydantic import BaseModel

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings


class Settings(BaseModel):
    db_settings: DBConfig
    app_settings: APPConfig
    scheduler: SchedulerSettings

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
        return cls(
            db_settings=DBConfig(**data["db_settings"]),
            app_settings=APPConfig(**data["app_settings"]),
            scheduler=SchedulerSettings(**data["scheduler"]),
        )


settings = Settings.load()
