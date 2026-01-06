"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware with proper security settings.
    
    Args:
        app: FastAPI application instance
    """
    # Parse allowed origins from settings
    allowed_origins = []
    
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        # Split by comma and strip whitespace
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
        allowed_origins.extend(origins)
    elif hasattr(settings, 'ALLOWED_ORIGINS') and settings.ALLOWED_ORIGINS:
        # Use ALLOWED_ORIGINS from config
        allowed_origins.extend(settings.ALLOWED_ORIGINS)
    
    # Production origins - always allowed
    prod_origins = [
        "https://outreach.hellonotionhive.com",
        "http://outreach.hellonotionhive.com",
    ]
    allowed_origins.extend(prod_origins)
    
    # Add development origins if not in production
    if not settings.is_production:
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
        allowed_origins.extend(dev_origins)
    
    # Remove duplicates and empty strings
    allowed_origins = list(set(filter(None, allowed_origins)))
    
    # Ensure we have at least one allowed origin
    if not allowed_origins:
        raise ValueError(
            "No CORS origins configured. Set CORS_ORIGINS environment variable."
        )
    
    print(f"Configuring CORS with allowed origins: {allowed_origins}")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
        expose_headers=[
            "X-Process-Time",
            "X-User-ID",
            "X-Request-ID",
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )
