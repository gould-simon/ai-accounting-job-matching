"""API endpoints for user preferences."""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import DatabaseError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.preferences import (
    JobPreferences,
    NotificationPreferences,
    SearchPreferences
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/job-preferences",
    response_model=JobPreferences,
    description="Get user's job preferences"
)
async def get_job_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JobPreferences:
    """Get user's job preferences.
    
    Args:
        db: Database session
        current_user: Authenticated user
        
    Returns:
        User's job preferences
        
    Raises:
        HTTPException: If preferences not found
    """
    try:
        user_repo = UserRepository(db)
        preferences = await user_repo.get_job_preferences(current_user.id)
        
        if not preferences:
            return JobPreferences()  # Return default preferences
            
        return preferences
        
    except DatabaseError as e:
        logger.error(
            "Failed to get job preferences",
            extra={
                "user_id": current_user.id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job preferences"
        )


@router.put(
    "/job-preferences",
    response_model=JobPreferences,
    description="Update user's job preferences"
)
async def update_job_preferences(
    preferences: JobPreferences,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JobPreferences:
    """Update user's job preferences.
    
    Args:
        preferences: New job preferences
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated job preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        user_repo = UserRepository(db)
        updated = await user_repo.update_job_preferences(
            user_id=current_user.id,
            preferences=preferences
        )
        return updated
        
    except DatabaseError as e:
        logger.error(
            "Failed to update job preferences",
            extra={
                "user_id": current_user.id,
                "preferences": preferences.model_dump(),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job preferences"
        )


@router.get(
    "/notification-preferences",
    response_model=NotificationPreferences,
    description="Get user's notification preferences"
)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> NotificationPreferences:
    """Get user's notification preferences.
    
    Args:
        db: Database session
        current_user: Authenticated user
        
    Returns:
        User's notification preferences
        
    Raises:
        HTTPException: If preferences not found
    """
    try:
        user_repo = UserRepository(db)
        preferences = await user_repo.get_notification_preferences(current_user.id)
        
        if not preferences:
            return NotificationPreferences()  # Return default preferences
            
        return preferences
        
    except DatabaseError as e:
        logger.error(
            "Failed to get notification preferences",
            extra={
                "user_id": current_user.id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification preferences"
        )


@router.put(
    "/notification-preferences",
    response_model=NotificationPreferences,
    description="Update user's notification preferences"
)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> NotificationPreferences:
    """Update user's notification preferences.
    
    Args:
        preferences: New notification preferences
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated notification preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        user_repo = UserRepository(db)
        updated = await user_repo.update_notification_preferences(
            user_id=current_user.id,
            preferences=preferences
        )
        return updated
        
    except DatabaseError as e:
        logger.error(
            "Failed to update notification preferences",
            extra={
                "user_id": current_user.id,
                "preferences": preferences.model_dump(),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


@router.get(
    "/search-preferences",
    response_model=SearchPreferences,
    description="Get user's search preferences"
)
async def get_search_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SearchPreferences:
    """Get user's search preferences.
    
    Args:
        db: Database session
        current_user: Authenticated user
        
    Returns:
        User's search preferences
        
    Raises:
        HTTPException: If preferences not found
    """
    try:
        user_repo = UserRepository(db)
        preferences = await user_repo.get_search_preferences(current_user.id)
        
        if not preferences:
            return SearchPreferences()  # Return default preferences
            
        return preferences
        
    except DatabaseError as e:
        logger.error(
            "Failed to get search preferences",
            extra={
                "user_id": current_user.id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search preferences"
        )


@router.put(
    "/search-preferences",
    response_model=SearchPreferences,
    description="Update user's search preferences"
)
async def update_search_preferences(
    preferences: SearchPreferences,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SearchPreferences:
    """Update user's search preferences.
    
    Args:
        preferences: New search preferences
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated search preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        user_repo = UserRepository(db)
        updated = await user_repo.update_search_preferences(
            user_id=current_user.id,
            preferences=preferences
        )
        return updated
        
    except DatabaseError as e:
        logger.error(
            "Failed to update search preferences",
            extra={
                "user_id": current_user.id,
                "preferences": preferences.model_dump(),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update search preferences"
        )
