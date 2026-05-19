from rest_assured.src.models.users import User
from rest_assured.src.repositories.users import get_user_by_email
from rest_assured.src.services.auth.passwords import verify_password


async def authenticate_user(session_factory, email: str, password: str) -> User | None:
    session = session_factory()
    try:
        user = await get_user_by_email(session, email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user
    finally:
        await session.close()
