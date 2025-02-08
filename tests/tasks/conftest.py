"""Test fixtures for task tests."""
import pytest
from unittest.mock import Mock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base


@pytest.fixture
async def db_session():
    """Create test database session."""
    # Create test database engine
    engine = create_async_engine(
        settings.TEST_DATABASE_URL,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_cv_service():
    """Mock CV service."""
    mock = Mock()
    mock.extract_text = AsyncMock()
    mock.delete_file = AsyncMock()
    return mock


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service."""
    mock = Mock()
    mock.analyze_cv = AsyncMock()
    mock.generate_embedding = AsyncMock()
    return mock


@pytest.fixture
def mock_job_repository():
    """Mock job repository."""
    mock = Mock()
    mock.get_jobs_needing_embedding_update = AsyncMock()
    mock.update = AsyncMock()
    mock.get_expired_jobs = AsyncMock()
    mock.get_users_for_match_refresh = AsyncMock()
    mock.get_latest_cv = AsyncMock()
    mock.get_user_preferences = AsyncMock()
    mock.find_matching_jobs = AsyncMock()
    mock.update_user_job_matches = AsyncMock()
    return mock


@pytest.fixture
def mock_maintenance_repository():
    """Mock maintenance repository."""
    mock = Mock()
    mock.cleanup_old_logs = AsyncMock()
    mock.get_inactive_users = AsyncMock()
    mock.archive_user_data = AsyncMock()
    mock.vacuum_analyze = AsyncMock()
    mock.update_statistics = AsyncMock()
    mock.check_table_bloat = AsyncMock()
    mock.check_database = AsyncMock()
    mock.check_openai_api = AsyncMock()
    mock.check_disk_space = AsyncMock()
    mock.check_memory_usage = AsyncMock()
    mock.check_cpu_usage = AsyncMock()
    return mock
