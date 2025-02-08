"""Tests for job matching service."""
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.job import Job
from app.services.job_matching import JobMatchingService, JobRecommendationService


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def job_matching_service(mock_db_session):
    """Create job matching service with mock session."""
    return JobMatchingService(mock_db_session)


@pytest.fixture
def job_recommendation_service(mock_db_session):
    """Create job recommendation service with mock session."""
    return JobRecommendationService(mock_db_session)


@pytest.fixture
def test_jobs():
    """Create test job objects without saving to database."""
    now = datetime.now(timezone.utc)
    return [
        Job(
            id=1,
            job_title="Senior Auditor",
            location="London",
            seniority="Senior",
            service="Audit",
            industry="Accounting",
            employment="Full-time",
            salary="Competitive",
            firm_id=1,
            embedding=[-0.1 for _ in range(1536)],
            description="Senior role in audit team",
            link="https://example.com/job1",
            req_no="JOB001",
            date_published="2025-02-08",
            created_at=now,
            updated_at=now,
            location_coordinates="51.5074° N, 0.1278° W",
            scrapped_industry="Accounting",
            scrapped_seniority="Senior",
            scrapped_service="Audit",
            slug="senior-auditor-london",
            is_indexed=True
        ),
        Job(
            id=2,
            job_title="Tax Associate",
            location="Manchester",
            seniority="Associate",
            service="Tax",
            industry="Accounting",
            employment="Full-time",
            salary="Competitive",
            firm_id=1,
            embedding=[0.1 for _ in range(1536)],
            description="Junior role in tax team",
            link="https://example.com/job2",
            req_no="JOB002",
            date_published="2025-02-08",
            created_at=now,
            updated_at=now,
            location_coordinates="53.4808° N, 2.2426° W",
            scrapped_industry="Accounting",
            scrapped_seniority="Associate",
            scrapped_service="Tax",
            slug="tax-associate-manchester",
            is_indexed=True
        ),
    ]


@pytest.mark.asyncio
async def test_search_jobs(
    job_matching_service: JobMatchingService,
    mock_db_session,
    test_jobs,
):
    """Test searching jobs."""
    # Mock database query result
    mock_result = AsyncMock()
    mock_result.all.return_value = [(test_jobs[0], 0.9)]
    mock_db_session.execute.return_value = mock_result

    # Test with embedding
    jobs = await job_matching_service.search_jobs(
        embedding=[-0.1 for _ in range(1536)],
        limit=10,
    )
    assert len(jobs) == 1
    assert jobs[0]["job_title"] == "Senior Auditor"

    # Test with preferences
    mock_result = AsyncMock()
    mock_result.all.return_value = [(test_jobs[1], 0.8)]
    mock_db_session.execute.return_value = mock_result
    
    jobs = await job_matching_service.search_jobs(
        embedding=[-0.1 for _ in range(1536)],
        preferences={
            "location": "Manchester",
            "service": "Tax",
        },
        limit=10,
    )
    assert len(jobs) == 1
    assert jobs[0]["job_title"] == "Tax Associate"


@pytest.mark.asyncio
async def test_generate_job_matches(
    job_matching_service: JobMatchingService,
    mock_db_session,
    test_jobs,
):
    """Test generating job matches."""
    # Mock database query result
    mock_result = AsyncMock()
    mock_result.all.return_value = [(test_jobs[0], 0.9)]
    mock_db_session.execute.return_value = mock_result

    matches = await job_matching_service.generate_job_matches(
        telegram_id=123456789,
        cv_embedding=[-0.1 for _ in range(1536)],
        preferences={
            "location": "London",
            "service": "Audit",
        },
    )
    assert len(matches) == 1
    assert matches[0]["job_title"] == "Senior Auditor"


@pytest.mark.asyncio
async def test_save_job_matches(
    job_matching_service: JobMatchingService,
    mock_db_session,
    test_jobs,
):
    """Test saving job matches."""
    # Mock database operations
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    
    matches = [
        {
            "job_id": test_jobs[0].id,
            "score": 0.9,
            "job_title": "Senior Auditor",
            "location": "London",
            "service": "Audit",
            "seniority": "Senior",
            "description": "Senior role in audit team",
        }
    ]
    saved = await job_matching_service.save_job_matches(
        telegram_id=123456789,
        matches=matches,
    )
    assert len(saved) == 1
    assert saved[0]["job_id"] == test_jobs[0].id
    assert saved[0]["score"] == 0.9


@pytest.mark.asyncio
async def test_generate_recommendations(
    job_recommendation_service: JobRecommendationService,
    mock_db_session,
    test_jobs,
):
    """Test generating recommendations."""
    # Mock database query results
    mock_result = AsyncMock()
    mock_result.all.return_value = [(test_jobs[0], 0.9)]
    mock_db_session.execute.return_value = mock_result

    # Mock user repo
    mock_user = MagicMock()
    mock_user.last_recommendations = None
    mock_user.cv_embedding = [-0.1 for _ in range(1536)]
    mock_user.preferences = {}

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_telegram_id.return_value = mock_user
    job_recommendation_service.user_repo = mock_user_repo

    recommendations = await job_recommendation_service.generate_recommendations(
        telegram_id=123456789,
        cv_embedding=[-0.1 for _ in range(1536)],
        preferences={
            "location": "London",
            "service": "Audit",
        },
    )
    assert len(recommendations) == 1
    assert recommendations[0]["job_title"] == "Senior Auditor"
