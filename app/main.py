"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db.session import engine
from app.db.base import Base
from app.core.cache import cache_manager
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.cors import setup_cors
from app.middleware.error_handler import error_handler_middleware
from app.middleware.logging import logging_middleware
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Handles startup and shutdown operations.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    print("🚀 Starting NH Outreach Agent API...")
    
    # Create database tables
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        if not settings.is_production:
            try:
                print("📊 Creating database tables...")
                await conn.run_sync(Base.metadata.create_all)
                print("✅ Database tables created successfully")
            except Exception as e:
                # Tables might already exist, that's okay
                print(f"⚠️  Database tables might already exist: {str(e)[:100]}")
                print("✅ Continuing with existing database schema")
    
    # Connect to Redis
    print("📡 Connecting to Redis...")
    await cache_manager.connect()
    
    # Configure rate limiter storage
    limiter.storage_uri = settings.REDIS_URL
    
    print("✅ Application startup complete")
    print(f"🌍 Environment: {'Production' if settings.is_production else 'Development'}")
    print(f"🔒 CORS origins: {settings.ALLOWED_ORIGINS}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down NH Outreach Agent API...")
    
    # Disconnect from Redis
    await cache_manager.disconnect()
    
    # Close database connections
    await engine.dispose()
    
    print("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="NH Outreach Agent API",
    description="Backend API for web performance analysis and outreach automation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add rate limiter state
app.state.limiter = limiter

# Set up CORS
setup_cors(app)

# Add middleware (order matters - first added is outermost)
app.middleware("http")(logging_middleware)
app.middleware("http")(error_handler_middleware)

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        API information
    """
    return {
        "name": "NH Outreach Agent API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if not settings.is_production else "disabled in production",
    }


@app.get("/health")
async def health():
    """
    Quick health check endpoint.
    
    Returns:
        Health status
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not settings.is_production,
        log_level="info",
    )
