import os

from dynaconf import Dynaconf
from pydantic import BaseModel, Field

from rest_assured.src.configs.app.app import APPConfig
from rest_assured.src.configs.app.db import DBConfig
from rest_assured.src.configs.app.jwt import JWTConfig
from rest_assured.src.configs.app.metrics import MetricsConfig
from rest_assured.src.configs.app.notifications import NotificationsConfig
from rest_assured.src.configs.app.scheduler import SchedulerSettings
from rest_assured.src.configs.app.smtp import SmtpConfig


class Settings(BaseModel):
    db_settings: DBConfig
    app_settings: APPConfig
    jwt: JWTConfig
    scheduler: SchedulerSettings
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    smtp: SmtpConfig
    notifications: NotificationsConfig


_settings_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
env_settings = Dynaconf(
    settings_files=[os.path.join(_settings_root, "settings.toml")],
    env_prefix="DYNACONF",
)
settings = Settings(
    app_settings=env_settings["app_settings"],
    db_settings=env_settings["db_settings"],
    jwt=env_settings["jwt"],
    scheduler=env_settings["scheduler"],
    metrics=env_settings.get("metrics", {}),
    smtp=env_settings["smtp"],
    notifications=env_settings["notifications"],
)
