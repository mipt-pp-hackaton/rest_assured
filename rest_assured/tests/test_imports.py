def test_jose_import():
    from jose import jwt as jose_jwt  # noqa
    assert jose_jwt is not None

def test_passlib_import():
    from passlib.context import CryptContext  # noqa
    ctx = CryptContext(schemes=["bcrypt"])
    assert ctx.hash("x") != "x"