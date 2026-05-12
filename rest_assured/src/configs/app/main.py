from dynaconf import Dynaconf
from pydantic import BaseModel

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings
from rest_assured.src.configs.app.smtp import SmtpConfig


class Settings(BaseModel):
    db_settings: DBConfig
    app_settings: APPConfig
    scheduler: SchedulerSettings
    smtp: SmtpConfig
    notifications: NotificationsConfig


env_settings = Dynaconf(settings_files=["settings.toml", "settings.yml"], env_prefix="DYNACONF")
settings = Settings(
    app_settings=env_settings["app_settings"],
    db_settings=env_settings["db_settings"],
    scheduler=env_settings["scheduler"],
    smtp=env_settings["smtp"],
    notifications=env_settings["notifications"],
)
