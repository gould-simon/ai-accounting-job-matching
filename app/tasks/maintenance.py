"""System maintenance tasks."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.maintenance import MaintenanceRepository
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="cleanup_old_logs",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2100,  # 35 minutes
)
async def cleanup_old_logs(days: int = 30) -> Dict:
    """Clean up old log entries.
    
    Args:
        days: Number of days after which to delete logs
        
    Returns:
        Dict containing cleanup results
    """
    logger.info(f"Starting log cleanup for entries older than {days} days")
    
    try:
        db = AsyncSession()  # Get from your session factory
        maintenance_repo = MaintenanceRepository(db)
        
        deleted_count = await maintenance_repo.cleanup_old_logs(days)
        await db.commit()
        
        logger.info(f"Log cleanup complete. Deleted {deleted_count} entries")
        return {
            "success": True,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.exception("Error during log cleanup")
        raise
        
    finally:
        await db.close()


@celery_app.task(
    name="cleanup_inactive_users",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2100,  # 35 minutes
)
async def cleanup_inactive_users(days: int = 180) -> Dict:
    """Clean up inactive user data.
    
    Args:
        days: Number of days of inactivity before cleanup
        
    Returns:
        Dict containing cleanup results
    """
    logger.info(f"Starting cleanup of users inactive for {days} days")
    
    try:
        db = AsyncSession()  # Get from your session factory
        maintenance_repo = MaintenanceRepository(db)
        
        # Get inactive users
        inactive_users = await maintenance_repo.get_inactive_users(days)
        
        cleaned_count = 0
        for user in inactive_users:
            try:
                # Archive user data
                await maintenance_repo.archive_user_data(user.id)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to clean up user {user.id}: {str(e)}")
                
        await db.commit()
        
        logger.info(f"User cleanup complete. Cleaned {cleaned_count} users")
        return {
            "success": True,
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.exception("Error during user cleanup")
        raise
        
    finally:
        await db.close()


@celery_app.task(
    name="database_maintenance",
    soft_time_limit=3600,  # 1 hour
    time_limit=4200,  # 70 minutes
)
async def database_maintenance() -> Dict:
    """Perform database maintenance tasks.
    
    Returns:
        Dict containing maintenance results
    """
    logger.info("Starting database maintenance")
    
    try:
        db = AsyncSession()  # Get from your session factory
        maintenance_repo = MaintenanceRepository(db)
        
        # Vacuum analyze tables
        tables_analyzed = await maintenance_repo.vacuum_analyze()
        
        # Update statistics
        stats_updated = await maintenance_repo.update_statistics()
        
        # Check for bloat
        bloat_report = await maintenance_repo.check_table_bloat()
        
        logger.info("Database maintenance complete")
        return {
            "success": True,
            "tables_analyzed": tables_analyzed,
            "stats_updated": stats_updated,
            "bloat_report": bloat_report
        }
        
    except Exception as e:
        logger.exception("Error during database maintenance")
        raise
        
    finally:
        await db.close()


@celery_app.task(
    name="health_check",
    soft_time_limit=300,  # 5 minutes
    time_limit=360,  # 6 minutes
)
async def health_check() -> Dict:
    """Perform system health check.
    
    Returns:
        Dict containing health check results
    """
    logger.info("Starting system health check")
    
    try:
        db = AsyncSession()  # Get from your session factory
        maintenance_repo = MaintenanceRepository(db)
        
        # Check database connectivity
        db_status = await maintenance_repo.check_database()
        
        # Check OpenAI API
        openai_status = await maintenance_repo.check_openai_api()
        
        # Check disk space
        disk_status = await maintenance_repo.check_disk_space()
        
        # Check memory usage
        memory_status = await maintenance_repo.check_memory_usage()
        
        # Check CPU usage
        cpu_status = await maintenance_repo.check_cpu_usage()
        
        logger.info("Health check complete")
        return {
            "success": True,
            "database": db_status,
            "openai_api": openai_status,
            "disk": disk_status,
            "memory": memory_status,
            "cpu": cpu_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception("Error during health check")
        raise
        
    finally:
        await db.close()
