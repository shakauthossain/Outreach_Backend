"""Custom exception classes for the application."""

from typing import Any, Optional


class AppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", detail: Optional[Any] = None):
        super().__init__(message, status_code=401, detail=detail)


class AuthorizationError(AppException):
    """Raised when user doesn't have permission."""
    
    def __init__(self, message: str = "Permission denied", detail: Optional[Any] = None):
        super().__init__(message, status_code=403, detail=detail)


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found", detail: Optional[Any] = None):
        super().__init__(message, status_code=404, detail=detail)


class ValidationError(AppException):
    """Raised when validation fails."""
    
    def __init__(self, message: str = "Validation failed", detail: Optional[Any] = None):
        super().__init__(message, status_code=422, detail=detail)


class DuplicateError(AppException):
    """Raised when trying to create a duplicate resource."""
    
    def __init__(self, message: str = "Resource already exists", detail: Optional[Any] = None):
        super().__init__(message, status_code=409, detail=detail)


class ExternalAPIError(AppException):
    """Raised when external API call fails."""
    
    def __init__(self, message: str = "External API error", detail: Optional[Any] = None):
        super().__init__(message, status_code=502, detail=detail)


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", detail: Optional[Any] = None):
        super().__init__(message, status_code=429, detail=detail)


class DatabaseError(AppException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database error", detail: Optional[Any] = None):
        super().__init__(message, status_code=500, detail=detail)


class CacheError(AppException):
    """Raised when cache operation fails."""
    
    def __init__(self, message: str = "Cache error", detail: Optional[Any] = None):
        super().__init__(message, status_code=500, detail=detail)


class ConfigurationError(AppException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str = "Configuration error", detail: Optional[Any] = None):
        super().__init__(message, status_code=500, detail=detail)


class TokenExhaustedError(AppException):
    """Raised when API token quota is exhausted."""
    
    def __init__(self, message: str = "API token quota exhausted", detail: Optional[Any] = None):
        super().__init__(message, status_code=429, detail=detail)


class BulkOperationError(AppException):
    """Raised when bulk operation fails partially or completely."""
    
    def __init__(
        self,
        message: str = "Bulk operation failed",
        detail: Optional[Any] = None,
        successful_count: int = 0,
        failed_count: int = 0,
    ):
        self.successful_count = successful_count
        self.failed_count = failed_count
        super().__init__(message, status_code=207, detail=detail)  # 207 Multi-Status
