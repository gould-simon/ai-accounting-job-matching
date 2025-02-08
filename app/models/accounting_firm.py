"""SQLAlchemy model for accounting firms."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Date, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AccountingFirm(Base):
    """Model for accounting firms (read-only)."""
    
    __tablename__ = "JobsApp_accountingfirm"
    
    # Make the table read-only
    __table_args__ = {"info": {"read_only": True}}
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(1000))
    location: Mapped[str] = mapped_column(String(10000))
    ranking: Mapped[int] = mapped_column(Integer)
    about: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(String(100))
    logo: Mapped[str] = mapped_column(String(100))
    jobs_count: Mapped[int] = mapped_column(Integer)
    last_scraped: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[date] = mapped_column(Date)
    country: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(1000))
    link: Mapped[str] = mapped_column(String(1000))
    linkedin_link: Mapped[str] = mapped_column(String(1000))
    twitter_link: Mapped[str] = mapped_column(String(1000))
    
    # Relationships
    jobs = relationship("Job", back_populates="firm", viewonly=True)
