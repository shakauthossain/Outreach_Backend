"""Task status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.models.task import Task, TaskStatus, TaskType
from app.core.security import get_current_user
from app.models.user import User


router = APIRouter()


class TaskStatusResponse(BaseModel):
    """Response for task status"""
    task_id: str
    task_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a background task.
    
    Args:
        task_id: UUID of the task to check
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Task status information
    """
    try:
        # Query for task by task_id
        stmt = select(Task).where(Task.task_id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Convert enum values to strings for response
        return TaskStatusResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            status=task.status.value,
            progress=task.progress,
            current_step=task.current_step,
            total_items=task.total_items,
            processed_items=task.processed_items,
            result=task.result,
            error=task.error,
            started_at=task.started_at,
            completed_at=task.completed_at,
            created_at=task.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )
