"""Users API endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import context
from app.core.exceptions import JobMatchingError
from app.database import get_session
from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.services.cv_processing import cv_processing_service

router = APIRouter()


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Create new user.
    
    Args:
        user: User data
        session: Database session
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        user_obj = User(**user.dict())
        await context.user_repo.create(user_obj)
        return user_obj
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get user by Telegram ID.
    
    Args:
        telegram_id: Telegram user ID
        session: Database session
        
    Returns:
        User details
        
    Raises:
        HTTPException: If user not found
    """
    try:
        user = await context.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{telegram_id}", response_model=UserResponse)
async def update_user(
    telegram_id: int,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Update user.
    
    Args:
        telegram_id: Telegram user ID
        user_update: Updated user data
        session: Database session
        
    Returns:
        Updated user
        
    Raises:
        HTTPException: If update fails
    """
    try:
        user = await context.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        for field, value in user_update.dict(exclude_unset=True).items():
            setattr(user, field, value)

        await context.user_repo.update(user)
        return user
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{telegram_id}/cv", response_model=UserResponse)
async def upload_cv(
    telegram_id: int,
    cv_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Upload user CV.
    
    Args:
        telegram_id: Telegram user ID
        cv_file: CV file
        session: Database session
        
    Returns:
        Updated user
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        user = await context.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Process CV
        cv_bytes = await cv_file.read()
        cv_text = await cv_processing_service.extract_text(cv_bytes, cv_file.filename)
        if not cv_text:
            raise HTTPException(
                status_code=400,
                detail="Failed to process CV. Please make sure it's a valid PDF or DOC file."
            )

        # Update user
        user.cv_text = cv_text
        embedding = await context.embedding_service.create_embedding(cv_text)
        user.cv_embedding = embedding
        await context.user_repo.update(user)

        return user
    except JobMatchingError as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
