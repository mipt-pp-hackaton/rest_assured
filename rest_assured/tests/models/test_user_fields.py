"""Тесты на новые поля User: is_active, is_superuser, updated_at (T3).

Также проверяют отсутствие legacy-поля is_admin.
"""

from datetime import timedelta


def test_users_module_imports_cleanly():
    """Сanity-check: модуль импортируется без ошибок.

    Защищает от поломки column-inference SQLModel при добавлении/переименовании
    полей (например, при неверной обвязке `Literal` / `sa_column`).
    """
    import importlib

    module = importlib.import_module("rest_assured.src.models.users")
    assert hasattr(module, "User")


def test_user_is_active_defaults_to_true():
    from rest_assured.src.models.users import User

    user = User(email="a@b.c", password_hash="x")
    assert user.is_active is True


def test_user_is_superuser_defaults_to_false():
    from rest_assured.src.models.users import User

    user = User(email="a@b.c", password_hash="x")
    assert user.is_superuser is False


def test_user_updated_at_is_utc_aware():
    from rest_assured.src.models.users import User

    user = User(email="a@b.c", password_hash="x")
    assert user.updated_at.tzinfo is not None
    assert user.updated_at.tzinfo.utcoffset(user.updated_at) == timedelta(0)


def test_user_has_no_legacy_is_admin_attribute():
    """Поле is_admin должно быть переименовано в is_superuser и не существовать."""
    from rest_assured.src.models.users import User

    # На уровне класса (SQLModel/Pydantic field): не должно быть в model_fields.
    assert "is_admin" not in getattr(
        User, "model_fields", {}
    ), "Legacy field 'is_admin' must be removed from User model_fields"

    # На уровне таблицы: в колонках тоже не должно быть is_admin.
    column_names = {c.name for c in User.__table__.columns}
    assert (
        "is_admin" not in column_names
    ), "Legacy column 'is_admin' must be removed from users table"


def test_users_table_has_new_columns():
    """SQLModel-метаданные таблицы users содержат новые колонки."""
    from rest_assured.src.models.users import User

    column_names = {c.name for c in User.__table__.columns}
    assert "is_active" in column_names
    assert "is_superuser" in column_names
    assert "updated_at" in column_names


def test_user_is_active_column_is_non_nullable():
    from rest_assured.src.models.users import User

    col = User.__table__.columns["is_active"]
    assert col.nullable is False


def test_user_updated_at_column_is_timezone_aware():
    """updated_at должна быть DateTime(timezone=True), как и created_at."""
    from sqlalchemy import DateTime

    from rest_assured.src.models.users import User

    col = User.__table__.columns["updated_at"]
    assert isinstance(col.type, DateTime)
    assert getattr(col.type, "timezone", False) is True
