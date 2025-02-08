"""Test database fixtures."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_db_session(db_session: AsyncSession) -> None:
    """Test that the database session works."""
    try:
        # Execute a simple query
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar()
        
        # Check the result
        assert value == 1
    except Exception as e:
        pytest.fail(f"Database query failed: {str(e)}")
