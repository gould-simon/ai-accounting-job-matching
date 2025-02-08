"""Job-related background tasks."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JobProcessingError
from app.models.job import Job
from app.repositories.job import JobRepository
from app.services.openai import OpenAIService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="update_job_embeddings",
    soft_time_limit=3600,  # 1 hour
    time_limit=4200,  # 70 minutes
)
async def update_job_embeddings(batch_size: int = 100) -> Dict:
    """Update embeddings for jobs that need refreshing.
    
    Args:
        batch_size: Number of jobs to process in one batch
        
    Returns:
        Dict containing update results
    """
    logger.info("Starting job embeddings update")
    
    try:
        db = AsyncSession()  # Get from your session factory
        job_repo = JobRepository(db)
        openai_service = OpenAIService()
        
        # Get jobs needing updates
        jobs = await job_repo.get_jobs_needing_embedding_update(
            batch_size=batch_size
        )
        
        updated_count = 0
        for job in jobs:
            try:
                # Generate job description for embedding
                job_text = (
                    f"{job.job_title}\n"
                    f"{job.company_name}\n"
                    f"{job.location}\n"
                    f"{job.description}\n"
                    f"{job.requirements}"
                )
                
                # Generate new embedding
                embedding = await openai_service.generate_embedding(job_text)
                
                # Update job
                job.embedding = embedding
                job.embedding_updated_at = datetime.utcnow()
                await job_repo.update(job)
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update job {job.id}: {str(e)}")
                
        await db.commit()
        
        logger.info(f"Job embeddings update complete. Updated {updated_count} jobs")
        return {
            "success": True,
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.exception("Error during job embeddings update")
        raise
        
    finally:
        await db.close()


@celery_app.task(
    name="cleanup_expired_jobs",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2100,  # 35 minutes
)
async def cleanup_expired_jobs() -> Dict:
    """Clean up expired job listings.
    
    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting expired jobs cleanup")
    
    try:
        db = AsyncSession()  # Get from your session factory
        job_repo = JobRepository(db)
        
        # Get expired jobs
        expired_jobs = await job_repo.get_expired_jobs()
        
        # Archive expired jobs
        archived_count = 0
        for job in expired_jobs:
            try:
                job.status = "archived"
                job.archived_at = datetime.utcnow()
                await job_repo.update(job)
                archived_count += 1
            except Exception as e:
                logger.error(f"Failed to archive job {job.id}: {str(e)}")
                
        await db.commit()
        
        logger.info(f"Job cleanup complete. Archived {archived_count} jobs")
        return {
            "success": True,
            "archived_count": archived_count
        }
        
    except Exception as e:
        logger.exception("Error during job cleanup")
        raise
        
    finally:
        await db.close()


@celery_app.task(
    name="refresh_job_matches",
    soft_time_limit=3600,  # 1 hour
    time_limit=4200,  # 70 minutes
)
async def refresh_job_matches(
    user_id: Optional[int] = None,
    batch_size: int = 100
) -> Dict:
    """Refresh job matches for users.
    
    Args:
        user_id: Optional specific user to refresh matches for
        batch_size: Number of users to process in one batch
        
    Returns:
        Dict containing refresh results
    """
    logger.info(f"Starting job matches refresh for {'all users' if user_id is None else f'user {user_id}'}")
    
    try:
        db = AsyncSession()  # Get from your session factory
        job_repo = JobRepository(db)
        
        # Get users to process
        users = await job_repo.get_users_for_match_refresh(
            user_id=user_id,
            batch_size=batch_size
        )
        
        updated_count = 0
        for user in users:
            try:
                # Get user's CV and preferences
                cv = await job_repo.get_latest_cv(user.id)
                preferences = await job_repo.get_user_preferences(user.id)
                
                if cv and cv.embedding:
                    # Find matching jobs
                    matches = await job_repo.find_matching_jobs(
                        cv_embedding=cv.embedding,
                        preferences=preferences,
                        limit=50
                    )
                    
                    # Update user's job matches
                    await job_repo.update_user_job_matches(
                        user_id=user.id,
                        job_matches=matches
                    )
                    
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to refresh matches for user {user.id}: {str(e)}")
                
        await db.commit()
        
        logger.info(f"Job matches refresh complete. Updated {updated_count} users")
        return {
            "success": True,
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.exception("Error during job matches refresh")
        raise
        
    finally:
        await db.close()
