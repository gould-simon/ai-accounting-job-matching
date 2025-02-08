"""Pydantic models for job-related schemas."""
from datetime import date, datetime
from typing import Optional

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema


class AccountingFirm(BaseSchema):
    """Schema for accounting firm data."""
    
    id: int
    name: str
    location: str
    ranking: int
    about: str
    script: str
    logo: str
    jobs_count: int
    last_scraped: Optional[datetime] = None
    created_at: date
    updated_at: date
    country: str
    slug: str
    link: str
    linkedin_link: str
    twitter_link: str


class JobBase(BaseSchema):
    """Base schema for job data."""
    
    job_title: str = Field(..., description="Job title")
    seniority: str = Field(..., description="Seniority level")
    service: str = Field(..., description="Service area")
    industry: str = Field(..., description="Industry")
    location: str = Field(..., description="Job location")
    employment: str = Field(..., description="Employment type")
    salary: str = Field(..., description="Salary range")
    description: str = Field(..., description="Job description")
    link: str = Field(..., description="Job posting URL")
    req_no: str = Field(..., description="Requisition number")
    date_published: Optional[str] = Field(None, description="Publication date")
    location_coordinates: str = Field(..., description="Location coordinates")
    scrapped_industry: str
    scrapped_seniority: str
    scrapped_service: str
    slug: str
    is_indexed: bool


class Job(JobBase):
    """Schema for job response."""
    
    id: int
    firm_id: int
    created_at: date
    updated_at: date
    firm: AccountingFirm


class JobSearchParams(BaseSchema):
    """Schema for job search parameters."""
    
    title: Optional[str] = Field(None, description="Job title filter")
    location: Optional[str] = Field(None, description="Location filter")
    seniority: Optional[str] = Field(None, description="Seniority level filter")
    service: Optional[str] = Field(None, description="Service area filter")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")


class JobMatchBase(BaseSchema):
    """Base schema for job match data."""
    
    score: float = Field(..., ge=0, le=1, description="Match score")
    
    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Validate score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Score must be between 0 and 1")
        return v


class JobMatchCreate(JobMatchBase):
    """Schema for creating a job match."""
    
    telegram_id: int
    job_id: int


class JobMatch(JobMatchBase):
    """Schema for job match response."""
    
    id: int
    telegram_id: int
    job_id: int
    job: Job
    created_at: datetime
