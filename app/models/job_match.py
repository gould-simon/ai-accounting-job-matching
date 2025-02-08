"""SQLAlchemy models for job matching."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class JobMatch(Base):
    """Model for job matches and recommendations."""
    
    __tablename__ = "job_matches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("users.telegram_id")
    )
    job_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("JobsApp_job.id")
    )
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="job_matches")
    job = relationship("Job")
