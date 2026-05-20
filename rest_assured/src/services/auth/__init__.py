from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.users import User
from rest_assured.src.repositories.users import get_user_by_email
from rest_assured.src.services.auth.passwords import verify_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await get_user_by_email(self._session, email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user


__all__ = ["AuthService"]
