"""Pydantic schemas for API data validation."""
from app.schemas.base import (
    APIResponse,
    BaseAPIResponse,
    BaseSchema,
    PaginatedData,
    PaginatedResponse,
)
from app.schemas.job import (
    AccountingFirm,
    Job,
    JobBase,
    JobMatch,
    JobMatchBase,
    JobMatchCreate,
    JobSearchParams,
)
from app.schemas.user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
    UserSearch,
    UserSearchBase,
    UserSearchCreate,
    UserConversation,
    UserConversationBase,
    UserConversationCreate,
)

__all__ = [
    # Base schemas
    "APIResponse",
    "BaseAPIResponse",
    "BaseSchema",
    "PaginatedData",
    "PaginatedResponse",
    
    # Job schemas
    "AccountingFirm",
    "Job",
    "JobBase",
    "JobMatch",
    "JobMatchBase",
    "JobMatchCreate",
    "JobSearchParams",
    
    # User schemas
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserSearch",
    "UserSearchBase",
    "UserSearchCreate",
    "UserConversation",
    "UserConversationBase",
    "UserConversationCreate",
]
