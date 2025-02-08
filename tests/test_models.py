"""Test SQLAlchemy models with existing database."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AccountingFirm, Job, User, UserSearch


@pytest.mark.asyncio
async def test_read_accounting_firms(db_session: AsyncSession) -> None:
    """Test reading accounting firms from the database."""
    # Query total count
    result = await db_session.execute(
        select(func.count()).select_from(AccountingFirm)
    )
    count = result.scalar()
    
    # Ensure we have some firms
    assert count > 0, "No accounting firms found in database"
    
    # Query first firm
    result = await db_session.execute(
        select(AccountingFirm).limit(1)
    )
    firm = result.scalar_one()
    
    # Verify firm attributes
    assert firm.name, "Firm name is empty"
    assert firm.location, "Firm location is empty"
    assert isinstance(firm.ranking, int), "Firm ranking is not an integer"


@pytest.mark.asyncio
async def test_read_jobs(db_session: AsyncSession) -> None:
    """Test reading jobs from the database."""
    # Query total count
    result = await db_session.execute(
        select(func.count()).select_from(Job)
    )
    count = result.scalar()
    
    # Ensure we have some jobs
    assert count > 0, "No jobs found in database"
    
    # Query first job with firm relationship loaded
    result = await db_session.execute(
        select(Job)
        .options(selectinload(Job.firm))
        .limit(1)
    )
    job = result.scalar_one()
    
    # Verify job attributes
    assert job.job_title, "Job title is empty"
    assert job.location, "Job location is empty"
    assert job.firm_id, "Job has no firm_id"
    
    # Test relationship to firm
    assert job.firm, "Job-to-firm relationship failed"
    assert job.firm.id == job.firm_id, "Job-to-firm relationship mismatch"


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession) -> None:
    """Test creating a new user."""
    # Clean up any existing test data
    await db_session.execute(
        delete(UserSearch).where(UserSearch.telegram_id == 12345)
    )
    await db_session.execute(
        delete(User).where(User.telegram_id == 12345)
    )
    await db_session.flush()
    
    # Create test user
    user = User(
        telegram_id=12345,
        username="test_user",
        first_name="Test",
        last_name="User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    # Add user
    db_session.add(user)
    await db_session.flush()
    
    # Verify user was created
    result = await db_session.execute(
        select(User).where(User.telegram_id == 12345)
    )
    user = result.scalar_one()
    assert user.id is not None, "User ID not generated"
    
    # Create a search for the user
    search = UserSearch(
        telegram_id=user.telegram_id,
        search_query="test search",
        created_at=datetime.now(timezone.utc),
        structured_preferences={"location": "London"},
    )
    db_session.add(search)
    await db_session.flush()
    
    # Verify search was created and relationship works
    result = await db_session.execute(
        select(UserSearch)
        .options(selectinload(UserSearch.user))
        .where(UserSearch.telegram_id == user.telegram_id)
    )
    search = result.scalar_one()
    assert search.id is not None, "Search ID not generated"
    assert search.user.id == user.id, "User relationship failed"
    
    # Clean up (will be rolled back by fixture)
