"""Database configuration and session management.

This module provides the core database functionality including:
1. Async SQLAlchemy engine setup with connection pooling
2. Session management
3. Base model class
4. Dependency injection for FastAPI
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Ensure connections are valid before use
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Don't auto-flush - explicit is better than implicit
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.
    
    This context manager ensures proper cleanup of the session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    This generator is used by FastAPI for dependency injection.
    It ensures each request gets its own database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with get_session() as session:
        yield session


async def init_db() -> None:
    """Initialize database connection.
    
    This function is called during application startup to verify
    database connectivity and perform any necessary initialization.
    
    Raises:
        DatabaseError: If database connection fails
    """
    try:
        logger.debug("Testing database connection")
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error("Failed to initialize database", exc_info=True)
        raise DatabaseError("Failed to initialize database", original_error=e) from e


async def close_db() -> None:
    """Close database connections.
    
    This function is called during application shutdown to ensure
    all database connections are properly closed.
    """
    try:
        logger.debug("Closing database connections")
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", exc_info=True)
        raise DatabaseError("Failed to close database connections", original_error=e) from e
