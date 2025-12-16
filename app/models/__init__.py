"""
Models package initialization.
Import all models here for easy access and Alembic migrations.
"""
from app.models.lead import Lead
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskType
from app.models.email_template import EmailTemplate

__all__ = [
    "Lead",
    "User",
    "Task",
    "TaskStatus",
    "TaskType",
    "EmailTemplate",
]
