from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.configs.app.main import settings


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(url=settings.db.dsl, echo=True, future=True)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with async_session() as session:
            yield session
    finally:
        await engine.dispose()
