"""Tests for database configuration and session management."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.database import (
    Base,
    close_db,
    engine,
    get_db,
    get_session,
    init_db
)


@pytest.mark.asyncio
async def test_init_db():
    """Test database initialization."""
    # Should succeed
    await init_db()

    # Test with broken connection
    with pytest.raises(DatabaseError) as exc_info:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.database.engine", None)
            await init_db()
    
    assert exc_info.value.error_code == "DB_CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_close_db():
    """Test database cleanup."""
    # Should succeed
    await close_db()

    # Test with error during cleanup
    with pytest.raises(DatabaseError) as exc_info:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.database.engine", None)
            await close_db()
    
    assert exc_info.value.error_code == "DB_CLEANUP_ERROR"


@pytest.mark.asyncio
async def test_get_session():
    """Test session context manager."""
    async with get_session() as session:
        # Session should be active
        assert isinstance(session, AsyncSession)
        assert not session.is_active

        # Should be able to execute queries
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    # Session should be closed
    assert session.is_closed


@pytest.mark.asyncio
async def test_get_session_with_error():
    """Test session rollback on error."""
    with pytest.raises(DatabaseError):
        async with get_session() as session:
            # Trigger an error
            await session.execute(text("SELECT * FROM nonexistent_table"))

    # Session should be closed
    assert session.is_closed


@pytest.mark.asyncio
async def test_get_db():
    """Test FastAPI database dependency."""
    db_gen = get_db()
    session = await anext(db_gen)

    try:
        # Should be an active session
        assert isinstance(session, AsyncSession)
        assert not session.is_active

        # Should be able to execute queries
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    finally:
        # Clean up
        try:
            await db_gen.aclose()
        except Exception:
            pass

    # Session should be closed
    assert session.is_closed


@pytest.mark.asyncio
async def test_base_model():
    """Test base model class."""
    # Should be able to create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify tables were created
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ))
        assert result.scalar() > 0
