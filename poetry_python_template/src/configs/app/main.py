from dynaconf import Dynaconf
from pydantic import BaseModel

from poetry_python_template.src.configs.app.app import APPConfig
from poetry_python_template.src.configs.app.db import DBConfig


class Settings(BaseModel):
    app: APPConfig
    db: DBConfig


env_settings = Dynaconf(settings_file=["settings.toml", "settings.yml"])
settings = Settings(
    app=env_settings["app_settings"],
    db=env_settings["db_settings"],
)
