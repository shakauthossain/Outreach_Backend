"""Request/response logging middleware."""

import time
import json
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses.
    Includes timing information and request/response details.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response object
        """
        # Start timer
        start_time = time.time()
        
        # Get request details
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        
        # Log request
        print(f"→ {method} {url} from {client_host}")
        
        # Get user if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.id
            print(f"  User: {user_id}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            status_code = response.status_code
            status_emoji = "✓" if status_code < 400 else "✗"
            
            print(
                f"← {status_emoji} {method} {url} "
                f"→ {status_code} ({duration:.3f}s)"
            )
            
            # Add custom headers
            response.headers["X-Process-Time"] = str(duration)
            if user_id:
                response.headers["X-User-ID"] = str(user_id)
            
            return response
            
        except Exception as e:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Log error
            print(
                f"← ✗ {method} {url} "
                f"→ ERROR: {type(e).__name__}: {str(e)} ({duration:.3f}s)"
            )
            
            # Re-raise to be handled by error middleware
            raise


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Simple function-based logging middleware.
    Alternative to class-based LoggingMiddleware.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response object
    """
    start_time = time.time()
    
    # Log request
    print(
        f"→ {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    print(
        f"← {request.method} {request.url.path} "
        f"→ {response.status_code} ({duration:.3f}s)"
    )
    
    # Add timing header
    response.headers["X-Process-Time"] = str(duration)
    
    return response
