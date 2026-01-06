"""Global error handling middleware."""

import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import AppException


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Global error handling middleware.
    Catches all exceptions and returns appropriate JSON responses.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response object
    """
    try:
        response = await call_next(request)
        return response
        
    except AppException as e:
        # Custom application exceptions
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": e.message,
                "detail": e.detail,
                "status_code": e.status_code,
            },
        )
    
    except PydanticValidationError as e:
        # Pydantic validation errors
        # Safely convert errors to avoid serialization issues
        try:
            error_details = e.errors()
        except Exception:
            error_details = str(e)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": error_details,
                "status_code": 422,
            },
        )
    
    except SQLAlchemyError as e:
        # Database errors
        print(f"Database error: {str(e)}")
        print(traceback.format_exc())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database error",
                "detail": "An error occurred while accessing the database",
                "status_code": 500,
            },
        )
    
    except ValueError as e:
        # Value errors (often from invalid conversions)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid value",
                "detail": str(e),
                "status_code": 400,
            },
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error: {str(e)}")
        print(traceback.format_exc())
        
        # In production, don't expose internal error details
        from app.config import settings
        
        if settings.is_production:
            detail = "An unexpected error occurred"
        else:
            detail = f"{type(e).__name__}: {str(e)}"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": detail,
                "status_code": 500,
            },
        )
