"""CV processing background tasks."""
import logging
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CVProcessingError
from app.models.cv import CV
from app.repositories.cv import CVRepository
from app.services.cv import CVService
from app.services.openai import OpenAIService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_cv",
    bind=True,
    max_retries=3,
    soft_time_limit=300,  # 5 minutes
    time_limit=360,  # 6 minutes
)
async def process_cv(
    self,
    cv_id: int,
    file_path: str,
    user_id: int
) -> Dict:
    """Process a CV file asynchronously.
    
    Args:
        cv_id: ID of the CV record
        file_path: Path to the CV file
        user_id: ID of the user who uploaded the CV
        
    Returns:
        Dict containing processing results
    """
    logger.info(f"Processing CV {cv_id} for user {user_id}")
    
    try:
        # Initialize services
        db = AsyncSession()  # Get from your session factory
        cv_repo = CVRepository(db)
        cv_service = CVService()
        openai_service = OpenAIService()
        
        # Get CV record
        cv = await cv_repo.get(cv_id)
        if not cv:
            raise CVProcessingError(f"CV {cv_id} not found")
            
        # Extract text from CV
        text = await cv_service.extract_text(file_path)
        if not text:
            raise CVProcessingError("Failed to extract text from CV")
            
        # Analyze CV with OpenAI
        analysis = await openai_service.analyze_cv(text)
        
        # Generate embeddings
        embedding = await openai_service.generate_embedding(text)
        
        # Update CV record with results
        cv.status = "processed"
        cv.extracted_text = text
        cv.analysis = analysis
        cv.embedding = embedding
        
        await cv_repo.update(cv)
        await db.commit()
        
        logger.info(f"Successfully processed CV {cv_id}")
        return {
            "success": True,
            "cv_id": cv_id,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.exception(f"Error processing CV {cv_id}")
        # Retry with exponential backoff
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=e, countdown=retry_in)
        
    finally:
        await db.close()


@celery_app.task(
    name="cleanup_old_cvs",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2100,  # 35 minutes
)
async def cleanup_old_cvs(days: int = 30) -> Dict:
    """Clean up CV files older than specified days.
    
    Args:
        days: Number of days after which to delete CVs
        
    Returns:
        Dict containing cleanup results
    """
    logger.info(f"Starting CV cleanup for files older than {days} days")
    
    try:
        db = AsyncSession()  # Get from your session factory
        cv_repo = CVRepository(db)
        cv_service = CVService()
        
        # Get old CVs
        old_cvs = await cv_repo.get_older_than(days)
        
        deleted_count = 0
        for cv in old_cvs:
            try:
                # Delete file
                await cv_service.delete_file(cv.file_path)
                # Delete record
                await cv_repo.delete(cv.id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete CV {cv.id}: {str(e)}")
                
        await db.commit()
        
        logger.info(f"CV cleanup complete. Deleted {deleted_count} files")
        return {
            "success": True,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.exception("Error during CV cleanup")
        raise
        
    finally:
        await db.close()
