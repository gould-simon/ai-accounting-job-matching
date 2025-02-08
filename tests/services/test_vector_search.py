"""Tests for vector search service."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from app.core.exceptions import DatabaseError, OpenAIError
from app.models.cv import CV
from app.models.job import Job
from app.models.user import User
from app.services.vector_search import VectorSearchService


@pytest.fixture
def mock_openai_service():
    """Create mock OpenAI service."""
    mock = Mock()
    mock.generate_embedding = AsyncMock()
    return mock


@pytest.fixture
async def test_user(db_session):
    """Create test user."""
    user = User(
        telegram_id=123456,
        username="test_user",
        first_name="Test",
        last_name="User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_cv(db_session, test_user):
    """Create test CV."""
    cv = CV(
        user_id=test_user.id,
        file_path="/tmp/test.pdf",
        status="processed",
        extracted_text="Python developer with 5 years experience",
        analysis={
            "skills": ["Python", "SQL", "FastAPI"],
            "experience": "5 years",
            "education": "BSc Computer Science"
        },
        embedding=[0.1, 0.2, 0.3],  # Test embedding
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(cv)
    await db_session.commit()
    return cv


@pytest.fixture
async def test_job(db_session):
    """Create test job."""
    job = Job(
        title="Senior Python Developer",
        description="Looking for experienced Python developer",
        requirements="5+ years Python experience",
        status="active",
        embedding=[0.15, 0.25, 0.35],  # Similar to CV embedding
        posted_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    await db_session.commit()
    return job


@pytest.mark.asyncio
async def test_find_matching_jobs(
    db_session,
    test_cv,
    test_job,
    mock_openai_service
):
    """Test finding matching jobs for a CV."""
    # Setup
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute
    matches = await service.find_matching_jobs(
        cv_id=test_cv.id,
        min_score=0.5,
        limit=10
    )
    
    # Verify
    assert len(matches) > 0
    assert matches[0]["job"]["id"] == test_job.id
    assert matches[0]["score"] > 0.5
    assert "title" in matches[0]["job"]
    assert "description" in matches[0]["job"]


@pytest.mark.asyncio
async def test_find_matching_jobs_no_cv(
    db_session,
    mock_openai_service
):
    """Test finding matching jobs with non-existent CV."""
    # Setup
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute & Verify
    with pytest.raises(ValueError, match="CV .* not found"):
        await service.find_matching_jobs(cv_id=999)


@pytest.mark.asyncio
async def test_find_matching_jobs_no_embedding(
    db_session,
    test_cv,
    mock_openai_service
):
    """Test finding matching jobs with CV without embedding."""
    # Setup
    test_cv.embedding = None
    await db_session.commit()
    
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute & Verify
    with pytest.raises(ValueError, match="CV .* has no embedding"):
        await service.find_matching_jobs(cv_id=test_cv.id)


@pytest.mark.asyncio
async def test_find_matching_cvs(
    db_session,
    test_cv,
    test_job,
    mock_openai_service
):
    """Test finding matching CVs for a job."""
    # Setup
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute
    matches = await service.find_matching_cvs(
        job_id=test_job.id,
        min_score=0.5,
        limit=10
    )
    
    # Verify
    assert len(matches) > 0
    assert matches[0]["cv"]["id"] == test_cv.id
    assert matches[0]["score"] > 0.5
    assert "extracted_text" in matches[0]["cv"]
    assert "analysis" in matches[0]["cv"]


@pytest.mark.asyncio
async def test_update_job_embedding(
    db_session,
    test_job,
    mock_openai_service
):
    """Test updating job embedding."""
    # Setup
    mock_openai_service.generate_embedding.return_value = [0.4, 0.5, 0.6]
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute
    await service.update_job_embedding(test_job)
    
    # Verify
    assert test_job.embedding == [0.4, 0.5, 0.6]
    assert test_job.embedding_updated_at is not None
    mock_openai_service.generate_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_update_cv_embedding(
    db_session,
    test_cv,
    mock_openai_service
):
    """Test updating CV embedding."""
    # Setup
    mock_openai_service.generate_embedding.return_value = [0.4, 0.5, 0.6]
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute
    await service.update_cv_embedding(test_cv)
    
    # Verify
    assert test_cv.embedding == [0.4, 0.5, 0.6]
    assert test_cv.embedding_updated_at is not None
    mock_openai_service.generate_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_job_matches(
    db_session,
    test_user,
    test_cv,
    test_job,
    mock_openai_service
):
    """Test refreshing job matches for a user."""
    # Setup
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute
    matches = await service.refresh_job_matches(
        user_id=test_user.id,
        min_score=0.5,
        limit=10
    )
    
    # Verify
    assert len(matches) > 0
    assert matches[0]["job"]["id"] == test_job.id
    assert matches[0]["score"] > 0.5


@pytest.mark.asyncio
async def test_refresh_job_matches_no_cv(
    db_session,
    test_user,
    mock_openai_service
):
    """Test refreshing job matches for user without CV."""
    # Setup
    service = VectorSearchService(db_session, mock_openai_service)
    
    # Execute & Verify
    with pytest.raises(ValueError, match="No CV found for user"):
        await service.refresh_job_matches(user_id=test_user.id)
