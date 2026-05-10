"""Юнит-тесты для загрузчика настроек."""

import pytest

from rest_assured.src.configs.app.main import Settings


def test_load_missing_file_gives_clear_error(monkeypatch, tmp_path):
    """Если settings.toml отсутствует — ошибка подсказывает про settings.toml.example."""
    import rest_assured.src.configs.app.main as main_module

    fake_root = tmp_path
    fake_file = fake_root / "rest_assured" / "src" / "configs" / "app" / "main.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()

    monkeypatch.setattr(main_module, "__file__", str(fake_file))

    with pytest.raises(FileNotFoundError) as exc_info:
        Settings.load()

    msg = str(exc_info.value)
    assert "settings.toml" in msg
    assert "settings.toml.example" in msg
