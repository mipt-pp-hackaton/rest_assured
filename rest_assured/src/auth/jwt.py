from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

from rest_assured.src.configs.app.main import settings


def create_access_token(email: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(hours=settings.jwt.ttl_hours)
    )
    return jwt.encode(
        {"sub": email, "exp": expire},
        settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
    )


def decode_token_email(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt.secret, algorithms=[settings.jwt.algorithm])
        email: str | None = payload.get("sub")
        if email is None:
            raise _credentials_exc()
        return email
    except JWTError:
        raise _credentials_exc()


def _credentials_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
