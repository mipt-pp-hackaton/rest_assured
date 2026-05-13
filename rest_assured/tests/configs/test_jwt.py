from dynaconf import settings


def test_jwt_config_loaded():
    from rest_assured.src.configs.app.jwt import JWTConfig
    assert JWTConfig.secret
    assert JWTConfig.ttl_hours > 0
    assert JWTConfig.algorithm in ("HS256", "HS384", "HS512")

def test_jwt_env_override(monkeypatch):
    monkeypatch.setenv("DYNACONF_JWT__SECRET", "override-secret")

    settings.clean()
    settings.execute_loaders()

    assert settings.jwt.secret == "override-secret"