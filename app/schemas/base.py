"""Base Pydantic models for API schemas."""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configurations."""
    
    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model -> Pydantic conversion
        json_encoders={
            datetime: lambda v: v.isoformat(),  # ISO format for dates
        },
    )


class BaseAPIResponse(BaseSchema):
    """Base API response with status and metadata."""
    
    success: bool
    message: str | None = None
    error: str | None = None


DataT = TypeVar("DataT")


class APIResponse(BaseAPIResponse, Generic[DataT]):
    """Generic API response with data payload."""
    
    data: DataT | None = None


class PaginatedData(BaseSchema, Generic[DataT]):
    """Paginated data wrapper."""
    
    items: list[DataT]
    total: int
    page: int
    size: int
    pages: int


class PaginatedResponse(BaseAPIResponse, Generic[DataT]):
    """API response with paginated data."""
    
    data: PaginatedData[DataT] | None = None
