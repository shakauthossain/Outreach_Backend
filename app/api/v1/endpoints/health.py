"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.core.cache import cache_manager
from app.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "production" if settings.is_production else "development",
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with database and Redis connectivity.
    
    Args:
        db: Database session
        
    Returns:
        Detailed health status
    """
    checks = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
    }
    
    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = "healthy"
        else:
            checks["database"] = "unhealthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        if cache_manager.redis:
            await cache_manager.redis.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "not connected"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # Overall status
    overall_status = "healthy" if all(
        v == "healthy" for v in checks.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "checks": checks,
        "version": "1.0.0",
    }
