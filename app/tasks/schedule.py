"""Celery beat schedule configuration."""
from celery.schedules import crontab

beat_schedule = {
    # CV Tasks
    'cleanup-old-cvs': {
        'task': 'app.tasks.cv.cleanup_old_cvs',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': (30,)  # 30 days
    },
    
    # Job Tasks
    'update-job-embeddings': {
        'task': 'app.tasks.jobs.update_job_embeddings',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'args': (100,)  # Batch size
    },
    'cleanup-expired-jobs': {
        'task': 'app.tasks.jobs.cleanup_expired_jobs',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily
    },
    'refresh-job-matches': {
        'task': 'app.tasks.jobs.refresh_job_matches',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'args': (None, 50)  # No specific user, batch size 50
    },
    
    # Maintenance Tasks
    'cleanup-old-logs': {
        'task': 'app.tasks.maintenance.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
        'args': (30,)  # 30 days
    },
    'cleanup-inactive-users': {
        'task': 'app.tasks.maintenance.cleanup_inactive_users',
        'schedule': crontab(hour=4, minute=0),  # 4 AM daily
        'args': (180,)  # 180 days
    },
    'database-maintenance': {
        'task': 'app.tasks.maintenance.database_maintenance',
        'schedule': crontab(hour=5, minute=0),  # 5 AM daily
    },
    'health-check': {
        'task': 'app.tasks.maintenance.health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    }
}
