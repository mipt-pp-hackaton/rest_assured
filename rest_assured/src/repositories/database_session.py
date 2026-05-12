from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.configs.app.main import settings

_engine = None
_sessionmaker = None




def _get_engine():
    global _engine
    if _engine is None:
        kwargs = {}
        if getattr(settings.app_settings, "use_testcontainers", False):
            kwargs["poolclass"] = NullPool

        _engine = create_async_engine(
            url=settings.db_settings.dsl, echo=False, future=True, **kwargs
        )
    return _engine


def _get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker


def get_session() -> AsyncSession:
    """Возвращает новую асинхронную сессию (не генератор)."""
    return _get_sessionmaker()()
