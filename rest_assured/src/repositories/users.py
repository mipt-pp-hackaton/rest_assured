from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.users import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.exec(select(User).where(User.email == email))
    return result.one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    is_superuser: bool = False,
) -> User:
    user = User(email=email, password_hash=password_hash, is_superuser=is_superuser)
    session.add(user)
    # Commit at the repository layer (project convention: repos commit,
    # services compose). The unique-email constraint surfaces as an
    # IntegrityError at commit time.
    await session.commit()
    await session.refresh(user)
    return user
