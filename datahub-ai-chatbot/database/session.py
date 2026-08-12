from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.exc import IllegalStateChangeError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

log = structlog.get_logger()

_IN_MEMORY_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

if settings.USE_IN_MEMORY_DATABASE:
    _database_url = _IN_MEMORY_URL
else:
    _database_url = settings.DATABASE_URL

engine = create_async_engine(_database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped AsyncSession with crash-proof teardown.

    Streaming chat responses write DB rows (conversation history, image
    metadata) inside a background task that can outlive request teardown.  If a
    ``commit()`` from that task is still in flight when FastAPI tears the
    session down, an ``async with``-based ``close()`` raises
    ``IllegalStateChangeError`` and turns a healthy response into a 500
    ("Internal server error").  So instead of ``async with`` we roll back any
    dangling transaction on failure and only swallow teardown-only state
    errors: a fully-committed write is never lost, and an uncommitted open
    transaction is cleanly discarded instead of crashing the request.
    """
    session = async_session_factory()
    try:
        yield session
    except Exception:
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            log.warning("session_rollback_failed")
        raise
    finally:
        try:
            await session.close()
        except (IllegalStateChangeError, PendingRollbackError):
            # The session is already being committed by the in-flight background
            # task that owns it; nothing else to clean up here.
            log.warning("session_teardown_state_race")
        except Exception:  # noqa: BLE001
            log.exception("session_teardown_failed")


async def init_db() -> None:
    from database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
