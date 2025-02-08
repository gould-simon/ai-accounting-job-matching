"""API endpoints for CV operations."""
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import CVProcessingError, DatabaseError, OpenAIError
from app.models.user import User
from app.repositories.cv import CVRepository
from app.schemas.cv import CV, CVAnalysisResponse, CVUploadResponse
from app.services.cv_processor import CVProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=CVUploadResponse,
    status_code=status.HTTP_201_CREATED,
    description="Upload and process a CV file"
)
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CVUploadResponse:
    """Upload and process a CV file.
    
    Args:
        file: CV file (PDF or DOCX)
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Upload response with CV ID
        
    Raises:
        HTTPException: If file upload or processing fails
    """
    try:
        # Validate file type
        if file.content_type not in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be PDF or DOCX"
            )

        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        ext = Path(file.filename).suffix
        filename = f"{uuid4()}{ext}"
        file_path = upload_dir / filename

        # Save uploaded file
        try:
            with file_path.open("wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(
                "Failed to save uploaded file",
                extra={
                    "user_id": current_user.id,
                    "filename": file.filename,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file"
            )

        # Process CV
        cv_processor = CVProcessor(db)
        cv = await cv_processor.process_cv(
            user_id=current_user.id,
            file_path=str(file_path),
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=file.size
        )

        return CVUploadResponse(
            cv_id=cv.id,
            message="CV uploaded and processed successfully"
        )

    except CVProcessingError as e:
        logger.error(
            "CV processing failed",
            extra={
                "user_id": current_user.id,
                "filename": file.filename,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except OpenAIError as e:
        logger.error(
            "OpenAI API error",
            extra={
                "user_id": current_user.id,
                "filename": file.filename,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CV analysis service temporarily unavailable"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during CV upload",
            extra={
                "user_id": current_user.id,
                "filename": file.filename,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/{cv_id}",
    response_model=CV,
    description="Get CV details"
)
async def get_cv(
    cv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CV:
    """Get CV details.
    
    Args:
        cv_id: CV ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        CV details
        
    Raises:
        HTTPException: If CV not found or access denied
    """
    try:
        cv_repo = CVRepository(db)
        cv = await cv_repo.get_with_details(cv_id)

        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )

        if cv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return cv

    except DatabaseError as e:
        logger.error(
            "Database error getting CV",
            extra={
                "user_id": current_user.id,
                "cv_id": cv_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


@router.get(
    "/{cv_id}/analysis",
    response_model=CVAnalysisResponse,
    description="Get CV analysis"
)
async def analyze_cv(
    cv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CVAnalysisResponse:
    """Get CV analysis.
    
    Args:
        cv_id: CV ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        CV analysis
        
    Raises:
        HTTPException: If CV not found or analysis fails
    """
    try:
        # Get CV
        cv_repo = CVRepository(db)
        cv = await cv_repo.get_with_details(cv_id)

        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )

        if cv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Get analysis from OpenAI
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze the CV data and provide:
                        1. Suggested job roles based on experience and skills
                        2. Potential skill gaps for accounting roles
                        3. Summary of work experience
                        4. Summary of education
                        
                        Format as JSON with keys:
                        suggested_roles (list), skill_gaps (list),
                        experience_summary (string), education_summary (string)"""
                },
                {
                    "role": "user",
                    "content": str(cv.structured_data)
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        analysis = response.choices[0].message.content

        return CVAnalysisResponse(
            cv=cv,
            **analysis
        )

    except OpenAIError as e:
        logger.error(
            "OpenAI API error analyzing CV",
            extra={
                "user_id": current_user.id,
                "cv_id": cv_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CV analysis service temporarily unavailable"
        )
    except Exception as e:
        logger.error(
            "Error analyzing CV",
            extra={
                "user_id": current_user.id,
                "cv_id": cv_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/user/{user_id}/latest",
    response_model=CV,
    description="Get user's latest CV"
)
async def get_latest_cv(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CV:
    """Get user's latest CV.
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Latest CV
        
    Raises:
        HTTPException: If CV not found or access denied
    """
    try:
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        cv_repo = CVRepository(db)
        cv = await cv_repo.get_latest_by_user(user_id)

        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No CV found"
            )

        return cv

    except DatabaseError as e:
        logger.error(
            "Database error getting latest CV",
            extra={
                "user_id": current_user.id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
