"""Pydantic models for CV-related schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class CVExperienceBase(BaseSchema):
    """Base schema for CV experience data."""
    
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    location: Optional[str] = Field(None, description="Job location")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    is_current: bool = Field(False, description="Whether this is current job")
    description: Optional[str] = Field(None, description="Job description")
    skills: Optional[List[str]] = Field(None, description="Skills used in role")


class CVExperienceCreate(CVExperienceBase):
    """Schema for creating CV experience."""
    
    cv_id: int


class CVExperience(CVExperienceBase):
    """Schema for CV experience response."""
    
    id: int
    cv_id: int
    created_at: datetime


class CVEducationBase(BaseSchema):
    """Base schema for CV education data."""
    
    institution: str = Field(..., description="Institution name")
    degree: str = Field(..., description="Degree name")
    field_of_study: Optional[str] = Field(None, description="Field of study")
    location: Optional[str] = Field(None, description="Institution location")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    is_current: bool = Field(False, description="Whether this is current education")
    grade: Optional[str] = Field(None, description="Grade achieved")
    activities: Optional[List[str]] = Field(None, description="Activities and societies")


class CVEducationCreate(CVEducationBase):
    """Schema for creating CV education."""
    
    cv_id: int


class CVEducation(CVEducationBase):
    """Schema for CV education response."""
    
    id: int
    cv_id: int
    created_at: datetime


class CVBase(BaseSchema):
    """Base schema for CV data."""
    
    user_id: int = Field(..., description="User ID")
    original_filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="File content type")
    file_size: int = Field(..., description="File size in bytes")
    skills: Optional[List[str]] = Field(None, description="Extracted skills")


class CVCreate(CVBase):
    """Schema for creating CV."""
    
    file_path: str = Field(..., description="Path where file is stored")


class CV(CVBase):
    """Schema for CV response."""
    
    id: int
    raw_text: Optional[str] = Field(None, description="Extracted CV text")
    structured_data: Optional[dict] = Field(None, description="Structured CV data")
    created_at: datetime
    updated_at: datetime
    experiences: List[CVExperience] = Field([], description="Work experiences")
    education: List[CVEducation] = Field([], description="Education history")


class CVUploadResponse(BaseSchema):
    """Schema for CV upload response."""
    
    cv_id: int = Field(..., description="ID of created CV")
    message: str = Field(..., description="Success message")


class CVAnalysisResponse(BaseSchema):
    """Schema for CV analysis response."""
    
    cv: CV
    suggested_roles: List[str] = Field(..., description="Suggested job roles")
    skill_gaps: List[str] = Field(..., description="Identified skill gaps")
    experience_summary: str = Field(..., description="Summary of experience")
    education_summary: str = Field(..., description="Summary of education")
