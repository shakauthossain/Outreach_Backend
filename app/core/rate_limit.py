"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def _rate_limit_key_func(request: Request) -> str:
    """
    Custom key function for rate limiting.
    Uses authenticated user ID if available, otherwise falls back to IP address.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Rate limit key string
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Initialize limiter with Redis storage for distributed rate limiting
limiter = Limiter(
    key_func=_rate_limit_key_func,
    default_limits=["200/hour", "50/minute"],  # Conservative defaults
    storage_uri=None,  # Will be set from settings in main.py
    strategy="fixed-window",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception
        
    Returns:
        JSON response with rate limit error
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": exc.headers.get("Retry-After", "60"),
        },
        headers=exc.headers,
    )


# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    # Authentication endpoints - prevent brute force
    "auth_login": "5/minute",
    "auth_register": "3/minute",
    "auth_otp": "3/minute",
    "auth_refresh": "10/minute",
    
    # Expensive operations - PageSpeed API calls
    "speedtest_single": "10/minute",
    "speedtest_bulk": "2/minute",
    
    # AI/LLM operations - costly and rate-limited by providers
    "mail_generate": "20/hour",
    "punchline_generate": "30/hour",
    "recommendations_analyze": "15/minute",
    
    # Screenshot operations - browser automation
    "screenshot_capture": "20/minute",
    "screenshot_bulk": "5/minute",
    
    # GoHighLevel API operations
    "ghl_sync": "10/minute",
    "ghl_send_message": "30/minute",
    
    # Standard CRUD operations
    "leads_read": "100/minute",
    "leads_create": "50/minute",
    "leads_update": "50/minute",
    "leads_delete": "30/minute",
    
    # Bulk operations
    "bulk_operations": "5/minute",
    
    # Export operations
    "export_csv": "10/minute",
    
    # Health checks and monitoring
    "health_check": "60/minute",
}


def get_rate_limit(operation: str) -> str:
    """
    Get rate limit string for a specific operation.
    
    Args:
        operation: Operation name (key from RATE_LIMITS)
        
    Returns:
        Rate limit string (e.g., "10/minute")
    """
    return RATE_LIMITS.get(operation, "50/minute")
