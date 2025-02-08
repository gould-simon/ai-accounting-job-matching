"""Celery app configuration."""
import os
from celery import Celery
from app.core.config import settings
from app.tasks.schedule import beat_schedule

# Configure Celery
celery_app = Celery(
    "ai_accounting_jobs",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.cv",
        "app.tasks.jobs",
        "app.tasks.maintenance"
    ]
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,  # One task per worker at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    beat_schedule=beat_schedule  # Add the schedule
)

# Optional: Configure task routing
celery_app.conf.task_routes = {
    "app.tasks.cv.*": {"queue": "cv_processing"},
    "app.tasks.jobs.*": {"queue": "job_updates"},
    "app.tasks.maintenance.*": {"queue": "maintenance"},
}
