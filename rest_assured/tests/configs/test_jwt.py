from dynaconf import settings


def test_jwt_config_loaded():
    from rest_assured.src.configs.app.jwt import JWTConfig
    cfg = JWTConfig(
        secret=settings.JWT.secret,
        ttl_hours=settings.JWT.ttl_hours,
        algorithm=settings.JWT.algorithm,
    )
    assert cfg.secret
    assert cfg.ttl_hours > 0
    assert cfg.algorithm in ("HS256", "HS384", "HS512")

def test_jwt_env_override(monkeypatch):
    monkeypatch.setenv("DYNACONF_JWT__SECRET", "override-secret")

    settings.clean()
    settings.execute_loaders()

    assert settings.jwt.secret == "override-secret"