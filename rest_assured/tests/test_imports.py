import pytest


def test_pyjwt_import():
    import jwt  # noqa

    assert jwt is not None


def test_passlib_import():
    try:
        from passlib.hash import bcrypt

        test_password = "secret_password"
        hashed = bcrypt.hash(test_password)

        assert bcrypt.verify(test_password, hashed) is True
    except (ImportError, KeyError) as e:
        pytest.fail(f"Failed import passlib[bcrypt]: {e}")
