"""Schemas for user preferences."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Job type enum."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class WorkLocation(str, Enum):
    """Work location enum."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


class SeniorityLevel(str, Enum):
    """Seniority level enum."""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"


class NotificationType(str, Enum):
    """Notification type enum."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    BOTH = "both"
    NONE = "none"


class JobPreferences(BaseModel):
    """User's job preferences."""
    job_types: List[JobType] = Field(
        default=[JobType.FULL_TIME],
        description="Preferred job types"
    )
    work_locations: List[WorkLocation] = Field(
        default=[WorkLocation.HYBRID, WorkLocation.REMOTE],
        description="Preferred work locations"
    )
    seniority_levels: List[SeniorityLevel] = Field(
        default=[SeniorityLevel.MID],
        description="Preferred seniority levels"
    )
    min_salary: Optional[int] = Field(
        default=None,
        description="Minimum annual salary in GBP"
    )
    max_salary: Optional[int] = Field(
        default=None,
        description="Maximum annual salary in GBP"
    )
    preferred_locations: List[str] = Field(
        default=[],
        description="Preferred work locations (cities/regions)"
    )
    max_commute_distance: Optional[int] = Field(
        default=None,
        description="Maximum commute distance in miles"
    )
    skills: List[str] = Field(
        default=[],
        description="Required or preferred skills"
    )
    industries: List[str] = Field(
        default=[],
        description="Preferred industries"
    )
    excluded_companies: List[str] = Field(
        default=[],
        description="Companies to exclude from search"
    )


class NotificationPreferences(BaseModel):
    """User's notification preferences."""
    notification_type: NotificationType = Field(
        default=NotificationType.TELEGRAM,
        description="Preferred notification method"
    )
    email_frequency: str = Field(
        default="daily",
        description="Email notification frequency (daily/weekly/monthly)"
    )
    min_match_score: float = Field(
        default=0.7,
        ge=0,
        le=1,
        description="Minimum match score for notifications (0-1)"
    )
    notify_new_jobs: bool = Field(
        default=True,
        description="Notify about new matching jobs"
    )
    notify_expiring_jobs: bool = Field(
        default=True,
        description="Notify about jobs expiring soon"
    )
    notify_salary_updates: bool = Field(
        default=True,
        description="Notify about salary updates for matching jobs"
    )
    quiet_hours_start: Optional[int] = Field(
        default=22,
        ge=0,
        le=23,
        description="Start of quiet hours (24h format)"
    )
    quiet_hours_end: Optional[int] = Field(
        default=7,
        ge=0,
        le=23,
        description="End of quiet hours (24h format)"
    )


class SearchPreferences(BaseModel):
    """User's search preferences."""
    default_search_radius: int = Field(
        default=25,
        ge=0,
        description="Default search radius in miles"
    )
    default_sort: str = Field(
        default="relevance",
        description="Default sort order (relevance/date/salary)"
    )
    results_per_page: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Number of results per page"
    )
    save_search_history: bool = Field(
        default=True,
        description="Save search history"
    )
    include_similar_roles: bool = Field(
        default=True,
        description="Include similar role titles in search"
    )
    highlight_new_jobs: bool = Field(
        default=True,
        description="Highlight jobs posted in last 24h"
    )
