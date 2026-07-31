from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

_IN_MEMORY_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

if settings.USE_IN_MEMORY_DATABASE:
    _database_url = _IN_MEMORY_URL
else:
    _database_url = settings.DATABASE_URL

engine = create_async_engine(_database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    from database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
