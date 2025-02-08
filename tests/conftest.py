"""
PyTest configuration file containing test fixtures.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from unittest.mock import AsyncMock, MagicMock

from app.core.logging_config import setup_logging
from app.models.job import Job
from app.models.user import User


def pytest_configure(config):
    """Configure pytest."""
    # Load environment variables
    load_dotenv()

    # Set test environment
    os.environ["BOT_ENV"] = "test"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key"
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_bot_token"


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine."""
    # Get test database URL from environment
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    # Ensure we're using test database
    if "test" not in database_url and "_test" not in database_url:
        raise ValueError("Must use a test database for testing")

    # Create test engine
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    try:
        # Verify connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create test session
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session for unit tests."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging() -> None:
    """Set up logging for tests."""
    setup_logging(log_level="DEBUG")


@pytest.fixture
def mock_openai() -> MagicMock:
    """Create mock OpenAI client for testing."""
    mock = MagicMock()
    mock.embeddings.create = AsyncMock(
        return_value=MagicMock(
            data=[
                MagicMock(
                    embedding=[-0.1 for _ in range(1536)]
                )
            ]
        )
    )
    return mock


@pytest.fixture
def sample_job_data() -> Dict[str, Any]:
    """Create sample job data for testing."""
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "job_title": "Senior Auditor",
        "location": "London",
        "seniority": "Senior",
        "service": "Audit",
        "industry": "Accounting",
        "employment": "Full-time",
        "salary": "Competitive",
        "firm_id": 1,
        "embedding": [-0.1 for _ in range(1536)],
        "description": "Senior role in audit team",
        "link": "https://example.com/job1",
        "req_no": "JOB001",
        "date_published": "2025-02-08",
        "created_at": now,
        "updated_at": now,
        "location_coordinates": "51.5074° N, 0.1278° W",
        "scrapped_industry": "Accounting",
        "scrapped_seniority": "Senior",
        "scrapped_service": "Audit",
        "slug": "senior-auditor-london",
        "is_indexed": True,
    }


@pytest.fixture
def sample_job(sample_job_data: Dict[str, Any]) -> Job:
    """Create a sample job instance for testing."""
    return Job(**sample_job_data)


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Create sample user data for testing."""
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "cv_text": "Experienced accountant with 5 years in audit",
        "cv_embedding": [-0.1 for _ in range(1536)],
        "preferences": {
            "location": "London",
            "service": "Audit",
            "seniority": "Senior",
        },
        "created_at": now,
        "updated_at": now,
        "last_active": now,
    }


@pytest.fixture
def sample_user(sample_user_data: Dict[str, Any]) -> User:
    """Create a sample user instance for testing."""
    return User(**sample_user_data)
