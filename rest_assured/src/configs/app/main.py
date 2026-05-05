from dynaconf import Dynaconf
from pydantic import BaseModel

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.scheduler import SchedulerConfig


class Settings(BaseModel):
    app: APPConfig
    db: DBConfig
    scheduler: SchedulerConfig


env_settings = Dynaconf(settings_file=["settings.toml", "settings.yml"])
settings = Settings(
    app=env_settings["app_settings"],
    db=env_settings["db_settings"],
    scheduler=env_settings["scheduler"],
)
