"""Jobs API endpoints."""
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import context
from app.core.exceptions import JobMatchingError
from app.database import get_session
from app.models.job import Job
from app.schemas.job import JobSearchParams, JobResponse

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
async def search_jobs(
    params: JobSearchParams,
    session: AsyncSession = Depends(get_session),
) -> List[Job]:
    """Search for jobs with filters.
    
    Args:
        params: Search parameters
        session: Database session
        
    Returns:
        List of matching jobs
        
    Raises:
        HTTPException: If search fails
    """
    try:
        jobs, _ = await context.job_matching_service.search_jobs(params)
        return jobs
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> Job:
    """Get job by ID.
    
    Args:
        job_id: Job ID
        session: Database session
        
    Returns:
        Job details
        
    Raises:
        HTTPException: If job not found
    """
    try:
        job = await context.job_matching_service.job_repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
