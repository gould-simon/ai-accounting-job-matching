"""Tests for job-related tasks."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.models.job import Job
from app.models.user import User
from app.tasks.jobs import (
    update_job_embeddings,
    cleanup_expired_jobs,
    refresh_job_matches
)


@pytest.mark.asyncio
async def test_update_job_embeddings(
    db_session,
    mock_openai_service
):
    """Test updating job embeddings."""
    # Setup
    old_date = datetime.utcnow() - timedelta(days=7)
    new_date = datetime.utcnow() - timedelta(minutes=30)
    
    jobs = [
        Job(
            job_title="Old Job 1",
            company_name="Company A",
            description="Description 1",
            embedding_updated_at=old_date
        ),
        Job(
            job_title="Old Job 2",
            company_name="Company B",
            description="Description 2",
            embedding_updated_at=old_date
        ),
        Job(
            job_title="New Job",
            company_name="Company C",
            description="Description 3",
            embedding_updated_at=new_date
        )
    ]
    
    for job in jobs:
        db_session.add(job)
    await db_session.commit()
    
    mock_openai_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
    
    # Execute
    result = await update_job_embeddings(batch_size=10)
    
    # Verify
    assert result["success"] is True
    assert result["updated_count"] == 2  # Only old jobs updated
    
    # Check embeddings were updated
    updated_jobs = await db_session.query(Job).filter(
        Job.embedding_updated_at > old_date
    ).all()
    assert len(updated_jobs) == 2
    for job in updated_jobs:
        assert job.embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_cleanup_expired_jobs(db_session):
    """Test cleanup of expired jobs."""
    # Setup
    expired_date = datetime.utcnow() - timedelta(days=31)
    active_date = datetime.utcnow() - timedelta(days=15)
    
    jobs = [
        Job(
            job_title="Expired Job 1",
            posted_at=expired_date,
            status="active"
        ),
        Job(
            job_title="Expired Job 2",
            posted_at=expired_date,
            status="active"
        ),
        Job(
            job_title="Active Job",
            posted_at=active_date,
            status="active"
        )
    ]
    
    for job in jobs:
        db_session.add(job)
    await db_session.commit()
    
    # Execute
    result = await cleanup_expired_jobs()
    
    # Verify
    assert result["success"] is True
    assert result["archived_count"] == 2
    
    # Check jobs were archived
    archived_jobs = await db_session.query(Job).filter(
        Job.status == "archived"
    ).all()
    assert len(archived_jobs) == 2
    
    active_jobs = await db_session.query(Job).filter(
        Job.status == "active"
    ).all()
    assert len(active_jobs) == 1
    assert active_jobs[0].job_title == "Active Job"


@pytest.mark.asyncio
async def test_refresh_job_matches(
    db_session,
    mock_job_repository
):
    """Test refreshing job matches."""
    # Setup
    users = [
        User(id=1, telegram_id=123),
        User(id=2, telegram_id=456),
        User(id=3, telegram_id=789)
    ]
    
    for user in users:
        db_session.add(user)
    await db_session.commit()
    
    mock_job_repository.get_latest_cv.return_value = Mock(
        embedding=[0.1, 0.2, 0.3]
    )
    mock_job_repository.get_user_preferences.return_value = {
        "location": "London",
        "experience": "5+ years"
    }
    mock_job_repository.find_matching_jobs.return_value = [
        {"job_id": 1, "score": 0.9},
        {"job_id": 2, "score": 0.8}
    ]
    
    # Execute
    result = await refresh_job_matches(batch_size=10)
    
    # Verify
    assert result["success"] is True
    assert result["updated_count"] == 3
    
    # Check matches were updated
    assert mock_job_repository.update_user_job_matches.call_count == 3
    mock_job_repository.update_user_job_matches.assert_any_call(
        user_id=1,
        job_matches=[
            {"job_id": 1, "score": 0.9},
            {"job_id": 2, "score": 0.8}
        ]
    )


@pytest.mark.asyncio
async def test_refresh_job_matches_specific_user(
    db_session,
    mock_job_repository
):
    """Test refreshing job matches for specific user."""
    # Setup
    user = User(id=1, telegram_id=123)
    db_session.add(user)
    await db_session.commit()
    
    mock_job_repository.get_latest_cv.return_value = Mock(
        embedding=[0.1, 0.2, 0.3]
    )
    mock_job_repository.get_user_preferences.return_value = {
        "location": "London",
        "experience": "5+ years"
    }
    mock_job_repository.find_matching_jobs.return_value = [
        {"job_id": 1, "score": 0.9},
        {"job_id": 2, "score": 0.8}
    ]
    
    # Execute
    result = await refresh_job_matches(user_id=1, batch_size=10)
    
    # Verify
    assert result["success"] is True
    assert result["updated_count"] == 1
    
    # Check matches were updated only for specified user
    mock_job_repository.update_user_job_matches.assert_called_once_with(
        user_id=1,
        job_matches=[
            {"job_id": 1, "score": 0.9},
            {"job_id": 2, "score": 0.8}
        ]
    )
