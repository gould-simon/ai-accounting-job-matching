"""Tests for CV repository."""
import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError, UserError
from app.models.cv import CV, CVExperience, CVEducation
from app.models.user import User
from app.repositories.cv import CVRepository


@pytest.fixture
async def cv_repo(db_session: AsyncSession) -> CVRepository:
    """Create CV repository."""
    return CVRepository(db_session)


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample user."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def sample_cv(db_session: AsyncSession, sample_user: User) -> CV:
    """Create a sample CV."""
    cv = CV(
        user_id=sample_user.id,
        original_filename="test_cv.pdf",
        file_path="/path/to/test_cv.pdf",
        content_type="application/pdf",
        file_size=1024,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(cv)
    await db_session.commit()
    return cv


@pytest.mark.asyncio
async def test_create_cv(cv_repo: CVRepository, sample_user: User):
    """Test CV creation."""
    cv = await cv_repo.create_cv(
        user_id=sample_user.id,
        original_filename="new_cv.pdf",
        file_path="/path/to/new_cv.pdf",
        content_type="application/pdf",
        file_size=2048
    )
    
    assert cv.user_id == sample_user.id
    assert cv.original_filename == "new_cv.pdf"
    assert cv.file_path == "/path/to/new_cv.pdf"
    assert cv.content_type == "application/pdf"
    assert cv.file_size == 2048
    assert cv.created_at is not None
    assert cv.updated_at is not None


@pytest.mark.asyncio
async def test_get_with_details(
    cv_repo: CVRepository,
    sample_cv: CV,
    db_session: AsyncSession
):
    """Test getting CV with details."""
    # Add experience and education
    experience = CVExperience(
        cv_id=sample_cv.id,
        company="Test Company",
        title="Test Title",
        created_at=datetime.now(timezone.utc)
    )
    education = CVEducation(
        cv_id=sample_cv.id,
        institution="Test University",
        degree="Test Degree",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add_all([experience, education])
    await db_session.commit()

    cv = await cv_repo.get_with_details(sample_cv.id)
    assert cv is not None
    assert len(cv.extracted_experiences) == 1
    assert len(cv.extracted_educations) == 1
    assert cv.extracted_experiences[0].company == "Test Company"
    assert cv.extracted_educations[0].institution == "Test University"


@pytest.mark.asyncio
async def test_get_latest_by_user(
    cv_repo: CVRepository,
    sample_user: User,
    db_session: AsyncSession
):
    """Test getting latest CV."""
    # Create multiple CVs
    cvs = []
    for i in range(3):
        cv = CV(
            user_id=sample_user.id,
            original_filename=f"cv_{i}.pdf",
            file_path=f"/path/to/cv_{i}.pdf",
            content_type="application/pdf",
            file_size=1024,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        cvs.append(cv)
        db_session.add(cv)
    await db_session.commit()

    latest_cv = await cv_repo.get_latest_by_user(sample_user.id)
    assert latest_cv is not None
    assert latest_cv.original_filename == "cv_2.pdf"


@pytest.mark.asyncio
async def test_update_extracted_data(
    cv_repo: CVRepository,
    sample_cv: CV
):
    """Test updating extracted CV data."""
    cv = await cv_repo.update_extracted_data(
        cv_id=sample_cv.id,
        raw_text="Sample CV text",
        structured_data={"key": "value"},
        embedding=[0.1] * 1536,
        skills=["Python", "SQL"]
    )
    
    assert cv.raw_text == "Sample CV text"
    assert cv.structured_data == {"key": "value"}
    assert cv.embedding == [0.1] * 1536
    assert cv.skills == ["Python", "SQL"]
    assert cv.updated_at > sample_cv.updated_at

    # Test non-existent CV
    with pytest.raises(UserError):
        await cv_repo.update_extracted_data(
            cv_id=999,
            raw_text="text",
            structured_data={},
            embedding=[0.1] * 1536,
            skills=[]
        )


@pytest.mark.asyncio
async def test_add_experience(
    cv_repo: CVRepository,
    sample_cv: CV
):
    """Test adding work experience."""
    experience = await cv_repo.add_experience(
        cv_id=sample_cv.id,
        company="Test Company",
        title="Software Engineer",
        location="London",
        start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        description="Test description",
        skills=["Python", "SQL"]
    )
    
    assert experience.cv_id == sample_cv.id
    assert experience.company == "Test Company"
    assert experience.title == "Software Engineer"
    assert experience.location == "London"
    assert experience.skills == ["Python", "SQL"]

    # Test non-existent CV
    with pytest.raises(UserError):
        await cv_repo.add_experience(
            cv_id=999,
            company="Company",
            title="Title"
        )


@pytest.mark.asyncio
async def test_add_education(
    cv_repo: CVRepository,
    sample_cv: CV
):
    """Test adding education."""
    education = await cv_repo.add_education(
        cv_id=sample_cv.id,
        institution="Test University",
        degree="BSc Computer Science",
        field_of_study="Computer Science",
        location="London",
        start_date=datetime(2016, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2020, 6, 1, tzinfo=timezone.utc),
        grade="First Class",
        activities=["Programming Club", "Chess Club"]
    )
    
    assert education.cv_id == sample_cv.id
    assert education.institution == "Test University"
    assert education.degree == "BSc Computer Science"
    assert education.field_of_study == "Computer Science"
    assert education.grade == "First Class"
    assert education.activities == ["Programming Club", "Chess Club"]

    # Test non-existent CV
    with pytest.raises(UserError):
        await cv_repo.add_education(
            cv_id=999,
            institution="University",
            degree="Degree"
        )


@pytest.mark.asyncio
async def test_get_cvs_without_embeddings(
    cv_repo: CVRepository,
    sample_cv: CV,
    db_session: AsyncSession
):
    """Test getting CVs without embeddings."""
    # Update sample CV with raw text but no embedding
    sample_cv.raw_text = "Sample text"
    await db_session.commit()

    cvs = await cv_repo.get_cvs_without_embeddings()
    assert len(cvs) == 1
    assert cvs[0].id == sample_cv.id

    # Update CV with embedding
    sample_cv.embedding = [0.1] * 1536
    await db_session.commit()

    cvs = await cv_repo.get_cvs_without_embeddings()
    assert len(cvs) == 0


@pytest.mark.asyncio
async def test_find_similar_cvs(
    cv_repo: CVRepository,
    sample_cv: CV,
    db_session: AsyncSession
):
    """Test finding similar CVs."""
    # Update sample CV with embedding
    sample_cv.embedding = [0.1] * 1536
    await db_session.commit()

    # Create another CV with different embedding
    cv2 = CV(
        user_id=sample_cv.user_id,
        original_filename="cv2.pdf",
        file_path="/path/to/cv2.pdf",
        content_type="application/pdf",
        file_size=1024,
        embedding=[0.2] * 1536,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(cv2)
    await db_session.commit()

    # Search with embedding similar to first CV
    similar_cvs = await cv_repo.find_similar_cvs(
        embedding=[0.1] * 1536,
        min_similarity=0.5
    )
    
    assert len(similar_cvs) > 0
    # First result should be the most similar CV
    assert similar_cvs[0][0].id == sample_cv.id
    # Each result should have a similarity score
    assert all(isinstance(score, float) for _, score in similar_cvs)
