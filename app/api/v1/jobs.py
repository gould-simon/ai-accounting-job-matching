"""API endpoints for job operations."""
import logging
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import DatabaseError
from app.models.user import User
from app.repositories.cv import CVRepository
from app.repositories.job import JobRepository
from app.schemas.job import Job, JobMatch, JobSearchParams

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/search",
    response_model=List[Job],
    description="Search for jobs"
)
async def search_jobs(
    params: JobSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> List[Job]:
    """Search for jobs using filters.
    
    Args:
        params: Search parameters
        db: Database session
        current_user: Optional authenticated user
        
    Returns:
        List of matching jobs
        
    Raises:
        HTTPException: If search fails
    """
    try:
        job_repo = JobRepository(db)
        jobs, total = await job_repo.search_jobs(
            title=params.title,
            location=params.location,
            seniority=params.seniority,
            service=params.service,
            skip=params.skip,
            limit=params.limit
        )
        return jobs

    except DatabaseError as e:
        logger.error(
            "Database error searching jobs",
            extra={
                "user_id": current_user.id if current_user else None,
                "params": params.model_dump(),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


@router.get(
    "/{job_id}",
    response_model=Job,
    description="Get job details"
)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Job:
    """Get job details.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Optional authenticated user
        
    Returns:
        Job details
        
    Raises:
        HTTPException: If job not found
    """
    try:
        job_repo = JobRepository(db)
        job = await job_repo.get_with_firm(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        return job

    except DatabaseError as e:
        logger.error(
            "Database error getting job",
            extra={
                "user_id": current_user.id if current_user else None,
                "job_id": job_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


@router.get(
    "/matches",
    response_model=List[JobMatch],
    description="Get job matches based on CV"
)
async def get_job_matches(
    min_score: float = Query(0.7, ge=0, le=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[JobMatch]:
    """Get job matches based on user's CV.
    
    Args:
        min_score: Minimum match score (0-1)
        limit: Maximum number of matches
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of job matches
        
    Raises:
        HTTPException: If matching fails or no CV found
    """
    try:
        # Get user's latest CV
        cv_repo = CVRepository(db)
        cv = await cv_repo.get_latest_by_user(current_user.id)

        if not cv or not cv.embedding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No CV found or CV not processed"
            )

        # Find matching jobs
        job_repo = JobRepository(db)
        matches = await job_repo.find_similar_jobs(
            embedding=cv.embedding,
            min_similarity=min_score,
            limit=limit
        )

        # Convert to JobMatch objects
        return [
            JobMatch(
                id=0,  # Not stored in database
                telegram_id=current_user.telegram_id,
                job_id=job.id,
                job=job,
                score=score
            )
            for job, score in matches
        ]

    except DatabaseError as e:
        logger.error(
            "Database error getting job matches",
            extra={
                "user_id": current_user.id,
                "min_score": min_score,
                "limit": limit,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


@router.get(
    "/recent",
    response_model=List[Job],
    description="Get recently posted jobs"
)
async def get_recent_jobs(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> List[Job]:
    """Get recently posted jobs.
    
    Args:
        days: Number of days to look back
        limit: Maximum number of jobs
        db: Database session
        current_user: Optional authenticated user
        
    Returns:
        List of recent jobs
        
    Raises:
        HTTPException: If query fails
    """
    try:
        job_repo = JobRepository(db)
        jobs = await job_repo.get_recent_jobs(
            days=days,
            limit=limit
        )
        return jobs

    except DatabaseError as e:
        logger.error(
            "Database error getting recent jobs",
            extra={
                "user_id": current_user.id if current_user else None,
                "days": days,
                "limit": limit,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
