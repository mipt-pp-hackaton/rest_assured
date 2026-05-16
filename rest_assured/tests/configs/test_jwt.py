import pytest
from rest_assured.src.configs.app.jwt import JWTConfig
from rest_assured.src.configs.app.main import settings, env_settings, Settings

def test_jwt_config_loaded():
    cfg = JWTConfig(
        secret=settings.jwt.secret,
        ttl_hours=settings.jwt.ttl_hours,
        algorithm=settings.jwt.algorithm,
    )
    assert cfg.secret
    assert cfg.ttl_hours > 0
    assert cfg.algorithm in ("HS256", "HS384", "HS512")

def test_jwt_env_override(monkeypatch):
    monkeypatch.setenv("DYNACONF_JWT__SECRET", "override-secret")

    env_settings.reload()

    overridden_settings = Settings(
        app_settings=env_settings["app_settings"],
        db_settings=env_settings["db_settings"],
        scheduler=env_settings["scheduler"],
        smtp=env_settings["smtp"],
        notifications=env_settings["notifications"],
        jwt=env_settings["jwt"],
    )

    assert overridden_settings.jwt.secret == "override-secret"

