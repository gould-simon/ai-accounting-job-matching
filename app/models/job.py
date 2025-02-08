"""SQLAlchemy model for jobs."""
from datetime import date
from typing import Optional, List

from sqlalchemy import String, Text, BigInteger, Date, Boolean, ForeignKey
from sqlalchemy.types import TypeDecorator, UserDefinedType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Vector(UserDefinedType):
    """PostgreSQL vector type for pgvector."""
    
    def __init__(self, dimensions: int) -> None:
        """Initialize vector type with dimensions."""
        self.dimensions = dimensions
    
    def get_col_spec(self, **kw) -> str:
        """Return column specification."""
        return f"vector({self.dimensions})"
    
    def bind_processor(self, dialect):
        """Process Python value -> DB value."""
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            if isinstance(value, (list, tuple)):
                # Convert list to PostgreSQL vector literal
                return f"[{','.join(str(x) for x in value)}]"
            return str(value)
        return process
    
    def result_processor(self, dialect, coltype):
        """Process DB value -> Python value."""
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return value
            # Remove brackets and split on commas
            if isinstance(value, str):
                value = value.strip('[]')
                return [float(x) for x in value.split(',')]
            return value
        return process


class Job(Base):
    """Model for job listings (read-only)."""
    
    __tablename__ = "JobsApp_job"
    
    # Make the table read-only
    __table_args__ = {
        "info": {"read_only": True},
    }
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_title: Mapped[str] = mapped_column(String(1000))
    seniority: Mapped[str] = mapped_column(String(1000))
    service: Mapped[str] = mapped_column(String(1000))
    industry: Mapped[str] = mapped_column(String(1000))
    location: Mapped[str] = mapped_column(String(5000))
    employment: Mapped[str] = mapped_column(String(1000))
    salary: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(400))
    req_no: Mapped[str] = mapped_column(String(1000))
    date_published: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[date] = mapped_column(Date)
    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("JobsApp_accountingfirm.id"))
    location_coordinates: Mapped[str] = mapped_column(String(5000))
    scrapped_industry: Mapped[str] = mapped_column(String(1000))
    scrapped_seniority: Mapped[str] = mapped_column(String(1000))
    scrapped_service: Mapped[str] = mapped_column(String(1000))
    slug: Mapped[str] = mapped_column(String(6000))
    is_indexed: Mapped[bool] = mapped_column(Boolean)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536))
    
    # Relationships
    firm = relationship("AccountingFirm", back_populates="jobs", viewonly=True)
