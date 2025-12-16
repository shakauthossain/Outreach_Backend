"""
Database initialization and table creation.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
from app.db.session import engine
from app.models import lead, user  # Import all models here
import logging

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Create all database tables.
    This should be called once during application startup.
    
    Note: In production, use Alembic migrations instead.
    """
    try:
        async with engine.begin() as conn:
            # Create all tables defined in Base.metadata
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise


async def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Used for health checks.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
