"""Tests for job repository."""
import pytest
from datetime import date, timedelta
from typing import AsyncGenerator, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.models.job import Job
from app.models.accounting_firm import AccountingFirm
from app.repositories.job import JobRepository, JobMatchRepository


@pytest.fixture
async def job_repo(db_session: AsyncSession) -> JobRepository:
    """Create job repository."""
    return JobRepository(db_session)


@pytest.fixture
async def sample_jobs(db_session: AsyncSession) -> List[Job]:
    """Create sample jobs for testing."""
    # Create a sample firm
    firm = AccountingFirm(
        id=1,
        name="Test Firm",
        website="https://testfirm.com",
        location="London"
    )
    db_session.add(firm)
    
    # Create sample jobs
    jobs = [
        Job(
            id=1,
            job_title="Senior Accountant",
            seniority="Senior",
            service="Audit",
            industry="Financial Services",
            location="London",
            employment="Full-time",
            salary="£50,000 - £60,000",
            description="Test job 1",
            link="https://example.com/job/1",
            req_no="REQ001",
            created_at=date.today(),
            updated_at=date.today(),
            firm_id=1,
            embedding=[0.1] * 1536
        ),
        Job(
            id=2,
            job_title="Tax Manager",
            seniority="Manager",
            service="Tax",
            industry="Various",
            location="Manchester",
            employment="Full-time",
            salary="£60,000 - £70,000",
            description="Test job 2",
            link="https://example.com/job/2",
            req_no="REQ002",
            created_at=date.today() - timedelta(days=5),
            updated_at=date.today() - timedelta(days=5),
            firm_id=1,
            embedding=[0.2] * 1536
        ),
        Job(
            id=3,
            job_title="Junior Accountant",
            seniority="Junior",
            service="Audit",
            industry="Various",
            location="London",
            employment="Full-time",
            salary="£30,000 - £40,000",
            description="Test job 3",
            link="https://example.com/job/3",
            req_no="REQ003",
            created_at=date.today() - timedelta(days=10),
            updated_at=date.today() - timedelta(days=10),
            firm_id=1,
            embedding=None  # No embedding for testing get_jobs_without_embeddings
        )
    ]
    
    for job in jobs:
        db_session.add(job)
    
    await db_session.commit()
    return jobs


@pytest.mark.asyncio
async def test_get_with_firm(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test getting job with firm details."""
    job = await job_repo.get_with_firm(1)
    assert job is not None
    assert job.id == 1
    assert job.firm is not None
    assert job.firm.name == "Test Firm"


@pytest.mark.asyncio
async def test_search_jobs(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test job search with filters."""
    # Test title search
    jobs, total = await job_repo.search_jobs(title="Senior")
    assert total == 1
    assert len(jobs) == 1
    assert jobs[0].job_title == "Senior Accountant"

    # Test location search
    jobs, total = await job_repo.search_jobs(location="London")
    assert total == 2
    assert len(jobs) == 2

    # Test seniority search
    jobs, total = await job_repo.search_jobs(seniority="Manager")
    assert total == 1
    assert jobs[0].job_title == "Tax Manager"

    # Test service search
    jobs, total = await job_repo.search_jobs(service="Audit")
    assert total == 2
    assert all(job.service == "Audit" for job in jobs)

    # Test pagination
    jobs, total = await job_repo.search_jobs(limit=1)
    assert total == 3  # Total should be all jobs
    assert len(jobs) == 1  # But only 1 returned


@pytest.mark.asyncio
async def test_find_similar_jobs(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test finding similar jobs by embedding."""
    # Search with embedding similar to job 1
    similar_jobs = await job_repo.find_similar_jobs(
        embedding=[0.1] * 1536,
        min_similarity=0.5
    )
    
    assert len(similar_jobs) > 0
    # First result should be job 1 (most similar)
    assert similar_jobs[0][0].id == 1
    # Each result should have a similarity score
    assert all(isinstance(score, float) for _, score in similar_jobs)

    # Test with location filter
    similar_jobs = await job_repo.find_similar_jobs(
        embedding=[0.1] * 1536,
        location="Manchester"
    )
    assert len(similar_jobs) == 1
    assert similar_jobs[0][0].location == "Manchester"

    # Test with seniority filter
    similar_jobs = await job_repo.find_similar_jobs(
        embedding=[0.1] * 1536,
        seniority="Senior"
    )
    assert len(similar_jobs) == 1
    assert similar_jobs[0][0].seniority == "Senior"


@pytest.mark.asyncio
async def test_get_jobs_without_embeddings(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test getting jobs without embeddings."""
    jobs = await job_repo.get_jobs_without_embeddings()
    assert len(jobs) == 1
    assert jobs[0].id == 3
    assert jobs[0].embedding is None


@pytest.mark.asyncio
async def test_update_embedding(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test updating job embedding."""
    new_embedding = [0.5] * 1536
    await job_repo.update_embedding(3, new_embedding)
    
    # Verify embedding was updated
    job = await job_repo.get(3)
    assert job is not None
    assert job.embedding == new_embedding


@pytest.mark.asyncio
async def test_get_recent_jobs(
    job_repo: JobRepository,
    sample_jobs: List[Job]
):
    """Test getting recent jobs."""
    # Get jobs from last 7 days
    jobs = await job_repo.get_recent_jobs(days=7)
    assert len(jobs) == 2  # Should get jobs 1 and 2
    assert all(job.id in [1, 2] for job in jobs)
    
    # Get jobs from last 2 days
    jobs = await job_repo.get_recent_jobs(days=2)
    assert len(jobs) == 1  # Should only get job 1
    assert jobs[0].id == 1


@pytest.mark.asyncio
async def test_error_handling(
    job_repo: JobRepository
):
    """Test error handling in repository."""
    # Test non-existent job
    job = await job_repo.get_with_firm(999)
    assert job is None

    # Test invalid embedding update
    with pytest.raises(DatabaseError) as exc_info:
        await job_repo.update_embedding(999, [0.1] * 1536)
    assert exc_info.value.error_code == "DB_ERROR"

    # Test search with invalid filter
    with pytest.raises(DatabaseError):
        await job_repo.search_jobs(title="'; DROP TABLE jobs; --")
