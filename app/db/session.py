"""
Database session management with connection pooling and async support.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, QueuePool
from app.config import settings


# Create async engine with optimized connection pooling
if settings.DEBUG:
    # Use NullPool for development (no pooling arguments)
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"application_name": settings.APP_NAME},
            "command_timeout": 60,
            "timeout": 10,
            "ssl": "require",
            "prepared_statement_cache_size": 0  # Disable prepared statement cache to avoid schema change issues
        },
        execution_options={
            "isolation_level": "READ COMMITTED"
        }
    )
else:
    # Use QueuePool for production with connection pooling
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        connect_args={
            "server_settings": {"application_name": settings.APP_NAME},
            "command_timeout": 60,
            "timeout": 10,
            "ssl": "require",
            "prepared_statement_cache_size": 0  # Disable prepared statement cache to avoid schema change issues
        },
        execution_options={
            "isolation_level": "READ COMMITTED"
        }
    )

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Usage in FastAPI endpoints:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_connections():
    """
    Close all database connections.
    Call this during application shutdown.
    """
    await engine.dispose()
