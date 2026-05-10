from pydantic import SecretStr

from rest_assured.src.configs.app.db import DBConfig


def test_password_is_secret_str():
    cfg = DBConfig(
        host="localhost",
        port=5432,
        user="u",
        password="s3cret",
        name="d",
    )
    assert isinstance(cfg.password, SecretStr)
    assert cfg.password.get_secret_value() == "s3cret"
    assert "s3cret" not in repr(cfg)
    assert "s3cret" not in repr(cfg.password)
