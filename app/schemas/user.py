"""Pydantic models for user-related schemas."""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    """Base schema for user data."""
    
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseSchema):
    """Schema for updating user data."""
    
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cv_text: Optional[str] = None
    preferences: Optional[dict] = None


class User(UserBase):
    """Schema for user response."""
    
    id: int
    cv_text: Optional[str] = None
    cv_embedding: Optional[dict] = None
    preferences: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    last_active: Optional[datetime] = None


class UserSearchBase(BaseSchema):
    """Base schema for user search data."""
    
    search_query: str = Field(..., description="Search query text")
    structured_preferences: Optional[dict] = Field(
        None, 
        description="Structured search preferences",
    )


class UserSearchCreate(UserSearchBase):
    """Schema for creating a new search."""
    
    telegram_id: int


class UserSearch(UserSearchBase):
    """Schema for search response."""
    
    id: int
    telegram_id: int
    created_at: datetime


class UserConversationBase(BaseSchema):
    """Base schema for user conversation data."""
    
    message: str = Field(..., description="Message content")
    is_user: bool = Field(..., description="True if message is from user")


class UserConversationCreate(UserConversationBase):
    """Schema for creating a new conversation message."""
    
    telegram_id: int


class UserConversation(UserConversationBase):
    """Schema for conversation response."""
    
    id: int
    telegram_id: int
    created_at: datetime
