"""API routes for the job matching service."""
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    OpenAIError,
    RateLimitError,
    ValidationError,
)
from app.core.logging import get_logger, log_context
from app.core.rate_limit import rate_limit
from app.database import get_db
from app.repositories.cv import CVRepository
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository
from app.schemas.api import (
    CVUploadResponse,
    ErrorResponse,
    HealthResponse,
    JobResponse,
    JobSearchRequest,
    JobSearchResponse,
    UserPreferences,
    UserProfile,
)
from app.services.cv_processor import CVProcessor
from app.telegram_bot import bot

logger = get_logger(__name__)

# Create router
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    response_description="Service health status"
)
async def health_check() -> HealthResponse:
    """Check the health of the service and its dependencies.
    
    Returns:
        Health check response
    """
    # Check database
    db_status = True
    try:
        async with AsyncSession(settings.engine) as session:
            await session.execute("SELECT 1")
    except Exception as e:
        logger.error("Database health check failed", extra={"error": str(e)})
        db_status = False

    # Check OpenAI
    openai_status = True
    try:
        async with AsyncOpenAI(api_key=settings.OPENAI_API_KEY) as client:
            await client.embeddings.create(
                model="text-embedding-ada-002",
                input="test"
            )
    except Exception as e:
        logger.error("OpenAI health check failed", extra={"error": str(e)})
        openai_status = False

    return HealthResponse(
        status="healthy" if db_status and openai_status else "degraded",
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        openai=openai_status
    )


@router.post(
    "/search",
    response_model=JobSearchResponse,
    summary="Search for jobs",
    response_description="List of matching jobs"
)
@rate_limit(limit=60, window=60)
async def search_jobs(
    request: Request,
    search: JobSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> JobSearchResponse:
    """Search for jobs using natural language and filters.
    
    Args:
        request: FastAPI request
        search: Search parameters
        db: Database session
        
    Returns:
        List of matching jobs
        
    Raises:
        HTTPException: If search fails
    """
    try:
        # Create embedding for search query
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=search.query
        )
        embedding = response.data[0].embedding

        # Search jobs
        job_repo = JobRepository(db)
        jobs = await job_repo.find_similar_jobs(
            embedding=embedding,
            min_similarity=0.7,
            limit=search.limit or 10,
            location=search.location,
            seniority=search.seniority,
            service=search.service
        )

        return JobSearchResponse(
            jobs=[job for job, _ in jobs],
            total=len(jobs),
            query=search.query
        )

    except OpenAIError as e:
        logger.error(
            "OpenAI error during job search",
            extra={
                "query": search.query,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Search service temporarily unavailable"
        )
    except DatabaseError as e:
        logger.error(
            "Database error during job search",
            extra={
                "query": search.query,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during job search",
            extra={
                "query": search.query,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    response_description="Job details"
)
async def get_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get detailed information about a specific job.
    
    Args:
        job_id: Job ID
        request: FastAPI request
        db: Database session
        
    Returns:
        Job details
        
    Raises:
        HTTPException: If job not found or other error occurs
    """
    try:
        job_repo = JobRepository(db)
        job = await job_repo.get_with_firm(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )

        return JobResponse(
            job=job,
            firm=job.firm
        )

    except DatabaseError as e:
        logger.error(
            "Database error getting job",
            extra={
                "job_id": job_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )


@router.post(
    "/cv/upload",
    response_model=CVUploadResponse,
    summary="Upload CV",
    response_description="CV upload response"
)
@rate_limit(limit=10, window=60)
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResponse:
    """Upload and analyze a CV document.
    
    Args:
        request: FastAPI request
        file: CV file (PDF or DOCX)
        user_id: Optional user ID to associate CV with
        db: Database session
        
    Returns:
        CV analysis results
        
    Raises:
        HTTPException: If upload or analysis fails
    """
    try:
        # Validate file type
        if file.content_type not in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            raise ValidationError("File must be PDF or DOCX")

        # Save file
        filename = f"{uuid4()}{file.filename[file.filename.rfind('.'):]}"
        file_path = settings.UPLOAD_DIR / filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process CV
        cv_processor = CVProcessor(db)
        cv = await cv_processor.process_cv(
            user_id=user_id,
            file_path=str(file_path),
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=len(content)
        )

        return CVUploadResponse(
            cv_id=cv.id,
            message="CV uploaded and processed successfully"
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Error processing CV",
            extra={
                "filename": file.filename,
                "user_id": user_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process CV"
        )


@router.get(
    "/users/{user_id}",
    response_model=UserProfile,
    summary="Get user profile",
    response_description="User profile information"
)
async def get_user_profile(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Get a user's profile information.
    
    Args:
        user_id: User ID
        request: FastAPI request
        db: Database session
        
    Returns:
        User profile
        
    Raises:
        HTTPException: If user not found or other error occurs
    """
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_with_preferences(user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        cv_repo = CVRepository(db)
        latest_cv = await cv_repo.get_latest_by_user(user_id)

        return UserProfile(
            user=user,
            preferences=user.preferences,
            latest_cv=latest_cv
        )

    except DatabaseError as e:
        logger.error(
            "Database error getting user profile",
            extra={
                "user_id": user_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )


@router.put(
    "/users/{user_id}/preferences",
    response_model=UserPreferences,
    summary="Update preferences",
    response_description="Updated user preferences"
)
async def update_preferences(
    user_id: int,
    preferences: UserPreferences,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserPreferences:
    """Update a user's job preferences.
    
    Args:
        user_id: User ID
        preferences: New preferences
        request: FastAPI request
        db: Database session
        
    Returns:
        Updated preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        updated = await user_repo.update_preferences(
            user_id=user_id,
            **preferences.model_dump()
        )

        return UserPreferences(**updated.model_dump())

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(
            "Database error updating preferences",
            extra={
                "user_id": user_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )


@router.get("/bot/health")
async def bot_health():
    """Check Telegram bot health."""
    try:
        if not bot.application or not bot._setup_done:
            raise HTTPException(
                status_code=503,
                detail="Bot not initialized"
            )
            
        # Get bot info to verify token works
        bot_user = await bot.application.bot.get_me()
        
        return {
            "status": "ok",
            "bot_info": {
                "id": bot_user.id,
                "username": bot_user.username,
                "can_read_messages": True,
                "can_join_groups": bot_user.can_join_groups,
                "can_read_group_messages": bot_user.can_read_group_messages,
                "supports_inline_queries": bot_user.supports_inline_queries,
            },
            "setup_complete": bot._setup_done,
            "handlers": [
                handler.callback.__name__ 
                for handler in bot.application.handlers.values()
                for group in handler.values()
                for handler in group
            ] if bot.application.handlers else []
        }
    except Exception as e:
        logger.error("Bot health check failed", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Bot health check failed: {str(e)}"
        )
