"""Integration tests for vector search functionality."""
import pytest
from datetime import datetime, timezone

from app.models.cv import CV
from app.models.job import Job
from app.models.user import User
from app.services.cv_processor import CVProcessor
from app.services.job_processor import JobProcessor
from app.services.vector_search import VectorSearchService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_vector_search(db_session):
    """Test end-to-end vector search flow."""
    # 1. Create test user
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

    # 2. Create and process test CV
    cv = CV(
        user_id=user.id,
        file_path="/tmp/test.pdf",
        status="uploaded",
        original_text="""
        Senior Python Developer with 5 years of experience
        Skills: Python, FastAPI, SQLAlchemy, PostgreSQL, Redis
        Experience:
        - Built scalable APIs using FastAPI and SQLAlchemy
        - Implemented vector search using pgvector
        - Managed PostgreSQL databases
        Education: BSc Computer Science
        """,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(cv)
    await db_session.commit()

    cv_processor = CVProcessor(db_session)
    await cv_processor.process_cv(cv)

    # 3. Create and process test jobs
    jobs = [
        Job(  # High match
            title="Senior Python Developer",
            description="""
            Looking for an experienced Python developer to build APIs
            using FastAPI and SQLAlchemy. Must have experience with
            PostgreSQL and vector databases.
            """,
            requirements="5+ years Python experience",
            status="active",
            posted_at=datetime.now(timezone.utc)
        ),
        Job(  # Medium match
            title="Backend Developer",
            description="""
            Backend role working with Django and PostgreSQL.
            Some Python experience required.
            """,
            requirements="3+ years experience",
            status="active",
            posted_at=datetime.now(timezone.utc)
        ),
        Job(  # Low match
            title="Frontend Developer",
            description="""
            Looking for React developer with TypeScript experience.
            Must know modern frontend practices.
            """,
            requirements="3+ years frontend experience",
            status="active",
            posted_at=datetime.now(timezone.utc)
        )
    ]

    for job in jobs:
        db_session.add(job)
    await db_session.commit()

    job_processor = JobProcessor(db_session)
    for job in jobs:
        await job_processor.process_job(job)

    # 4. Perform vector search
    vector_search = VectorSearchService(db_session)
    matches = await vector_search.find_matching_jobs(
        cv_id=cv.id,
        min_score=0.5,
        limit=10
    )

    # 5. Verify results
    assert len(matches) >= 2  # Should match at least high and medium
    
    # First match should be high match job
    assert matches[0]["job"]["id"] == jobs[0].id
    assert matches[0]["score"] > 0.8  # High similarity
    
    # Second match should be medium match job
    assert matches[1]["job"]["id"] == jobs[1].id
    assert 0.6 < matches[1]["score"] < matches[0]["score"]
    
    # Frontend job should either not match or have very low score
    frontend_matches = [m for m in matches if m["job"]["id"] == jobs[2].id]
    if frontend_matches:
        assert frontend_matches[0]["score"] < 0.6

    # 6. Test reverse search (finding CVs for a job)
    cv_matches = await vector_search.find_matching_cvs(
        job_id=jobs[0].id,
        min_score=0.5,
        limit=10
    )

    assert len(cv_matches) > 0
    assert cv_matches[0]["cv"]["id"] == cv.id
    assert cv_matches[0]["score"] > 0.8  # High similarity

    # 7. Test job match refresh
    matches = await vector_search.refresh_job_matches(
        user_id=user.id,
        min_score=0.5,
        limit=10
    )

    assert len(matches) >= 2
    assert matches[0]["job"]["id"] == jobs[0].id
    assert matches[0]["score"] > 0.8
