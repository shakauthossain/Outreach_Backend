"""
Common schemas used across multiple endpoints.
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field, validator


# Generic type for paginated responses
T = TypeVar('T')


class PaginationParams(BaseModel):
    """Query parameters for pagination"""
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(default=50, ge=1, le=500, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate SQL offset from page and limit"""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    limit: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        """Factory method to create paginated response"""
        pages = (total + limit - 1) // limit  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class TaskResponse(BaseModel):
    """Response for background task creation"""
    task_id: str
    status: str
    message: str = "Task queued successfully"
    
    class Config:
        from_attributes = True


class BatchTaskResponse(BaseModel):
    """Response for bulk operation tasks"""
    batch_id: str
    task_ids: List[str]
    total_tasks: int
    message: str = "Batch operation queued successfully"


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(description="Overall health status: healthy, degraded, unhealthy")
    version: str
    environment: str
    components: dict = Field(description="Status of individual components")
    timestamp: str
