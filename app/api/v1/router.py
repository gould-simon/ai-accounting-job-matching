"""API router configuration."""
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.repositories.maintenance import MaintenanceRepository

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/v1")

@router.get("/health")
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """Check system health.
    
    Args:
        request: FastAPI request
        db: Database session
        
    Returns:
        Dict containing health status
    """
    try:
        start_time = datetime.utcnow()
        maintenance_repo = MaintenanceRepository(db)
        
        # Check components
        db_status = await maintenance_repo.check_database()
        openai_status = await maintenance_repo.check_openai_api()
        
        # Calculate response time
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "response_time": response_time,
            "components": {
                "database": db_status,
                "openai_api": openai_status
            }
        }
        
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """Get system metrics.
    
    Args:
        request: FastAPI request
        db: Database session
        
    Returns:
        Dict containing system metrics
    """
    try:
        maintenance_repo = MaintenanceRepository(db)
        
        # Get system metrics
        disk_status = await maintenance_repo.check_disk_space()
        memory_status = await maintenance_repo.check_memory_usage()
        cpu_status = await maintenance_repo.check_cpu_usage()
        
        # Get application metrics
        result = await db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM users WHERE status = 'active') as active_users,
                (SELECT COUNT(*) FROM cvs WHERE status = 'processed') as processed_cvs,
                (SELECT COUNT(*) FROM job_matches WHERE created_at > NOW() - INTERVAL '24 hours') as daily_matches,
                (SELECT COUNT(*) FROM system_logs WHERE level = 'ERROR' AND created_at > NOW() - INTERVAL '24 hours') as daily_errors
            """
        )
        app_metrics = result.fetchone()
        
        return {
            "system": {
                "disk": disk_status,
                "memory": memory_status,
                "cpu": cpu_status
            },
            "application": {
                "active_users": app_metrics.active_users,
                "processed_cvs": app_metrics.processed_cvs,
                "daily_matches": app_metrics.daily_matches,
                "daily_errors": app_metrics.daily_errors
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception("Failed to get metrics")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )
