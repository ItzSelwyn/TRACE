from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            yield session
    finally:
        await async_engine.dispose()
