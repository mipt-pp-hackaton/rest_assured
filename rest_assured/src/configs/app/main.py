from dynaconf import Dynaconf

from pydantic import BaseModel

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings


class Settings(BaseModel):
    db_settings: DBConfig
    app_settings: APPConfig
    scheduler: SchedulerSettings


env_settings = Dynaconf(
    settings_files=["settings.toml", "settings.yml"], env_prefix="DYNACONF"
)
settings = Settings(
    app=env_settings["app_settings"],
    db=env_settings["db_settings"],
    scheduler=env_settings["scheduler"],
)
