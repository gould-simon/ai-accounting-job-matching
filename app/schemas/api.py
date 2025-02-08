"""API request and response schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class JobBase(BaseModel):
    """Base schema for job data."""

    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    description: str = Field(..., description="Job description")
    requirements: str = Field(..., description="Job requirements")
    salary_range: Optional[str] = Field(None, description="Salary range if available")
    job_type: str = Field(..., description="Full-time, part-time, contract, etc.")
    experience_level: str = Field(..., description="Required experience level")
    posted_date: datetime = Field(..., description="When the job was posted")

    class Config:
        """Pydantic config."""
        from_attributes = True


class JobResponse(JobBase):
    """Response schema for job data."""

    id: int = Field(..., description="Job ID")
    url: str = Field(..., description="Job posting URL")
    match_score: Optional[float] = Field(
        None,
        description="Similarity score if returned as part of a search"
    )


class JobSearchRequest(BaseModel):
    """Request schema for job search."""

    query: str = Field(
        ...,
        description="Search query (can be natural language)",
        min_length=3
    )
    location: Optional[str] = Field(
        None,
        description="Filter by location"
    )
    job_type: Optional[str] = Field(
        None,
        description="Filter by job type"
    )
    experience_level: Optional[str] = Field(
        None,
        description="Filter by experience level"
    )
    min_salary: Optional[int] = Field(
        None,
        description="Minimum salary",
        gt=0
    )
    limit: int = Field(
        10,
        description="Maximum number of results",
        ge=1,
        le=100
    )

    @validator("query")
    def validate_query(cls, v: str) -> str:
        """Validate and clean search query.
        
        Args:
            v: Query string
            
        Returns:
            Cleaned query string
        """
        return v.strip()


class JobSearchResponse(BaseModel):
    """Response schema for job search."""

    total: int = Field(..., description="Total number of matches")
    results: List[JobResponse] = Field(..., description="List of matching jobs")
    query_embedding_id: Optional[int] = Field(
        None,
        description="ID of stored query embedding"
    )


class HealthResponse(BaseModel):
    """Response schema for health check."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    database: bool = Field(..., description="Database connection status")
    openai: bool = Field(..., description="OpenAI API status")


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    context: Optional[dict] = Field(None, description="Additional error context")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class CVUploadResponse(BaseModel):
    """Response schema for CV upload."""

    cv_id: int = Field(..., description="ID of uploaded CV")
    text_extracted: bool = Field(..., description="Whether text was extracted")
    num_tokens: int = Field(..., description="Number of tokens in extracted text")
    skills: List[str] = Field(..., description="Extracted skills")
    experience_years: Optional[float] = Field(
        None,
        description="Extracted years of experience"
    )
    suggested_roles: List[str] = Field(
        ...,
        description="AI-suggested roles based on CV"
    )


class UserPreferences(BaseModel):
    """Schema for user job preferences."""

    desired_roles: List[str] = Field(..., description="Desired job roles")
    locations: List[str] = Field(..., description="Preferred locations")
    min_salary: Optional[int] = Field(None, description="Minimum desired salary")
    job_types: List[str] = Field(..., description="Preferred job types")
    remote_only: bool = Field(False, description="Only show remote jobs")
    notifications_enabled: bool = Field(
        True,
        description="Whether to send job notifications"
    )

    @validator("desired_roles", "locations", "job_types")
    def validate_list_not_empty(cls, v: List[str]) -> List[str]:
        """Validate that lists are not empty.
        
        Args:
            v: List to validate
            
        Returns:
            Validated list
            
        Raises:
            ValueError: If list is empty
        """
        if not v:
            raise ValueError("List cannot be empty")
        return [x.strip() for x in v]


class UserProfile(BaseModel):
    """Schema for user profile data."""

    id: int = Field(..., description="User ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    cv_uploaded: bool = Field(..., description="Whether user has uploaded a CV")
    cv_last_updated: Optional[datetime] = Field(
        None,
        description="When CV was last updated"
    )
    preferences: Optional[UserPreferences] = Field(
        None,
        description="User's job preferences"
    )
    total_searches: int = Field(
        0,
        description="Total number of job searches"
    )
    created_at: datetime = Field(..., description="When user was created")
    last_active: datetime = Field(..., description="When user was last active")

    class Config:
        """Pydantic config."""
        from_attributes = True
