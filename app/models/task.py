"""
Task model for tracking background job progress.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Text, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
import enum


class TaskStatus(str, enum.Enum):
    """Task execution status"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class TaskType(str, enum.Enum):
    """Type of background task"""
    SPEED_TEST = "speed_test"
    PUNCHLINE_GENERATION = "punchline_generation"
    RECOMMENDATION_CAPTURE = "recommendation_capture"
    MAIL_GENERATION = "mail_generation"
    CSV_IMPORT = "csv_import"
    BULK_OPERATION = "bulk_operation"


class Task(Base):
    """
    Track background task execution for monitoring and debugging.
    """
    __tablename__ = "tasks"
    
    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Task Identification
    task_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Task Status
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Progress Tracking
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Results
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Resource References
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Retry Information
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('ix_tasks_status_created', 'status', 'created_at'),
        Index('ix_tasks_type_status', 'task_type', 'status'),
        Index('ix_tasks_batch_id', 'batch_id'),
        Index('ix_tasks_lead_user', 'lead_id', 'user_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"
    
    @property
    def is_complete(self) -> bool:
        """Check if task has finished (success or failure)"""
        return self.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
