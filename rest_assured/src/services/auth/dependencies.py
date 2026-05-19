from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from rest_assured.src.models.users import User
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.repositories.users import get_user_by_email
from rest_assured.src.services.auth.jwt import decode_token_email

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(_oauth2_scheme)) -> User:
    email = decode_token_email(token)
    session = get_session()
    try:
        user = await get_user_by_email(session, email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    finally:
        await session.close()
