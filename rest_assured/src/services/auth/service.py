from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.users import User
from rest_assured.src.repositories.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from rest_assured.src.schemas.auth import TokenPair
from rest_assured.src.schemas.users import UserCreate
from rest_assured.src.services.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from rest_assured.src.services.auth.passwords import hash_password, verify_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await get_user_by_email(self.session, email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None  # treat exactly like wrong creds — don't leak account state
        return user

    async def register(self, data: UserCreate) -> User:
        existing = await get_user_by_email(self.session, data.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        try:
            return await create_user(
                self.session,
                email=data.email,
                password_hash=hash_password(data.password),
                is_superuser=data.is_superuser,
            )
        except IntegrityError as e:
            # TOCTOU: two concurrent registrations for the same email both
            # pass get_user_by_email; the loser hits the unique constraint
            # at commit. Translate to 409 instead of leaking a 500.
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from e

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        try:
            user_id = int(payload.sub)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        user = await get_user_by_id(self.session, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        if user.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User row missing id after persistence",
            )
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )
