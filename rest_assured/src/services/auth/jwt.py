import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import HTTPException, status

from rest_assured.src.configs.app.main import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    exp: int
    iat: int
    token_type: str


def create_access_token(subject: str | int, *, ttl: timedelta | None = None) -> str:
    if ttl is None:
        ttl = timedelta(minutes=settings.jwt.access_token_ttl_minutes)
    return _encode(subject, ttl, "access")


def create_refresh_token(subject: str | int, *, ttl: timedelta | None = None) -> str:
    if ttl is None:
        ttl = timedelta(days=settings.jwt.refresh_token_ttl_days)
    return _encode(subject, ttl, "refresh")


def decode_token(token: str, *, expected_type: Literal["access", "refresh"]) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret.get_secret_value(),
            algorithms=[settings.jwt.algorithm],
        )
    except jwt.PyJWTError as e:
        logger.warning("JWT decode failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    sub = payload.get("sub")
    token_type = payload.get("token_type")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing token_type claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    exp_raw = payload.get("exp")
    iat_raw = payload.get("iat")
    if exp_raw is None or iat_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing exp/iat claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        exp = int(exp_raw)
        iat = int(iat_raw)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token exp/iat claims malformed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return TokenPayload(
        sub=str(sub),
        exp=exp,
        iat=iat,
        token_type=str(token_type),
    )


def _encode(subject: str | int, ttl: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "token_type": token_type,
    }
    return jwt.encode(
        claims,
        settings.jwt.secret.get_secret_value(),
        algorithm=settings.jwt.algorithm,
    )
