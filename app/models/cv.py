"""SQLAlchemy models for CV-related tables."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CV(Base):
    """Model for user CVs."""
    
    __tablename__ = "cvs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    structured_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[List[float]]] = mapped_column(ARRAY(float))
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="cvs")
    extracted_experiences = relationship("CVExperience", back_populates="cv")
    extracted_educations = relationship("CVEducation", back_populates="cv")


class CVExperience(Base):
    """Model for extracted work experience from CVs."""
    
    __tablename__ = "cv_experiences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(Integer, ForeignKey("cvs.id"), index=True)
    company: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    cv = relationship("CV", back_populates="extracted_experiences")


class CVEducation(Base):
    """Model for extracted education from CVs."""
    
    __tablename__ = "cv_educations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(Integer, ForeignKey("cvs.id"), index=True)
    institution: Mapped[str] = mapped_column(String)
    degree: Mapped[str] = mapped_column(String)
    field_of_study: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(default=False)
    grade: Mapped[Optional[str]] = mapped_column(String)
    activities: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    cv = relationship("CV", back_populates="extracted_educations")
