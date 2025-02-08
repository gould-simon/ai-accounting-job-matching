"""SQLAlchemy models for user-related tables."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, BigInteger, DateTime, Boolean, ForeignKey, Integer, Column, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.job_match import JobMatch  # Import JobMatch from its own module


class User(Base):
    """Model for Telegram bot users."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[Optional[str]] = mapped_column(String)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    cv_text: Mapped[Optional[str]] = mapped_column(Text)
    cv_embedding: Mapped[Optional[dict]] = mapped_column(JSONB)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB)
    notification_preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        server_default='{}',
        comment="User's notification preferences"
    )
    search_preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        server_default='{}',
        comment="User's search preferences"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_active: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        server_default="now()"
    )

    # Relationships
    searches = relationship("UserSearch", back_populates="user")
    conversations = relationship("UserConversation", back_populates="user")
    job_matches = relationship("JobMatch", back_populates="user")


class UserSearch(Base):
    """Model for user search history."""
    
    __tablename__ = "user_searches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_query: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("users.telegram_id")
    )
    structured_preferences: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Relationships
    user = relationship("User", back_populates="searches")


class UserConversation(Base):
    """Model for user conversation history."""
    
    __tablename__ = "user_conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    is_user: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("users.telegram_id"), 
        index=True
    )
    
    # Relationships
    user = relationship("User", back_populates="conversations")
