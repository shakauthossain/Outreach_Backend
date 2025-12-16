"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
celery_app = Celery(
    "nh_outreach_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    task_track_started=True,  # Track when task starts
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minute soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for long-running tasks
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    
    # Result backend settings
    result_expires=86400,  # Keep results for 24 hours
    result_persistent=True,  # Persist results to disk
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes between retries
    task_retry_jitter=True,  # Add randomness to backoff
    
    # Security
    task_send_sent_event=True,
    task_send_success_event=True,
    task_send_error_event=True,
)

# Import task modules to register them
from app.tasks import speedtest_tasks  # noqa
from app.tasks import punchline_tasks  # noqa
from app.tasks import recommendation_tasks  # noqa
from app.tasks import mail_tasks  # noqa

# Periodic tasks (optional)
celery_app.conf.beat_schedule = {
    # Example: Clean up old tasks daily
    "cleanup-old-results": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_results",
        "schedule": crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
}
