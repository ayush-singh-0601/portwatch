"""
Async SQLAlchemy engine and session factory for PostgreSQL (asyncpg).

Usage::

    from app.database import get_db

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Create the async engine — pool settings tuned for a mid-size deployment.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory.
# CRITICAL: expire_on_commit=False prevents lazy-load errors after commit
# when accessing attributes on ORM objects outside the session scope.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is automatically closed when the request completes.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
