"""
Unit tests for Telegram bot commands.
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, Chat
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from sqlalchemy.exc import DatabaseError

from app.telegram_bot import JobMatchingBot
from app.models.user import User
from app.core.exceptions import DatabaseError as AppDatabaseError


@pytest.fixture
def mock_update():
    """Create a mock update."""
    mock = MagicMock(spec=Update)
    mock.effective_user = MagicMock(spec=TelegramUser)
    mock.effective_user.id = 12345
    mock.effective_chat = MagicMock(spec=Chat)
    mock.effective_chat.id = 12345
    return mock


@pytest.fixture
def mock_context():
    """Create a mock context."""
    mock = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock.bot = MagicMock()
    return mock


@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_db_session():
    """Mock database session with proper cleanup."""
    session = AsyncMock()
    async def mock_close():
        await session.close()
    session.close = mock_close
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def mock_user_repo():
    """Mock user repository."""
    repo = AsyncMock()
    yield repo


@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        id=1,
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
        cv_text="Experienced accountant with 5 years of experience",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_jobs_command_no_user(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
):
    """Test /jobs command when user is not found."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup user repo
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = None

        try:
            # Execute
            await bot._jobs_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="❌ You need to set up your profile first. Use /profile to get started."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_jobs_command_database_error(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
):
    """Test /jobs command when database error occurs."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup user repo to raise DatabaseError
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.side_effect = AppDatabaseError("Test error")

        try:
            # Execute
            await bot._jobs_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="⚠️ Sorry, I encountered a database error. Please try again later."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_jobs_command_success(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
    sample_user: User,
):
    """Test /jobs command successful execution."""
    # Setup
    bot = JobMatchingBot()

    # Mock job matching service
    mock_matches = [
        MagicMock(
            title="Test Job",
            company="Test Company",
            location="Test Location",
            score=0.85
        )
    ]

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class, \
         patch("app.services.job_matching.JobMatchingService") as mock_job_service:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup mocks
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = sample_user
        mock_job_service.return_value.match_jobs_for_user.return_value = mock_matches

        try:
            # Execute
            await bot._jobs_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once()
            assert "Test Job" in mock_context.bot.send_message.call_args[1]["text"]
            assert "Test Company" in mock_context.bot.send_message.call_args[1]["text"]
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_profile_command_no_user(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
):
    """Test /profile command when user is not found."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup user repo
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = None

        try:
            # Execute
            await bot._profile_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="❌ No profile found. Use /start to create your profile."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_profile_command_database_error(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
):
    """Test /profile command when database error occurs."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup user repo to raise DatabaseError
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.side_effect = AppDatabaseError("Test error")

        try:
            # Execute
            await bot._profile_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="⚠️ Sorry, I encountered a database error. Please try again later."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_profile_command_success(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
    sample_user: User,
):
    """Test /profile command successful execution."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup user repo
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = sample_user

        try:
            # Execute
            await bot._profile_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once()
            assert "Profile Information" in mock_context.bot.send_message.call_args[1]["text"]
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_jobs_command_matching_error(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
    sample_user: User,
):
    """Test /jobs command when job matching fails."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class, \
         patch("app.services.job_matching.JobMatchingService") as mock_job_service:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup mocks
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = sample_user
        mock_job_service.return_value.match_jobs_for_user.side_effect = AppDatabaseError("Test error")

        try:
            # Execute
            await bot._jobs_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="⚠️ Sorry, I encountered an error while finding jobs. Please try again later."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_jobs_command_no_matches(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
    mock_user_repo: AsyncMock,
    sample_user: User,
):
    """Test /jobs command when no matches are found."""
    # Setup
    bot = JobMatchingBot()

    with patch("app.telegram_bot.get_session") as mock_get_session, \
         patch("app.telegram_bot.UserRepository") as mock_user_repo_class, \
         patch("app.services.job_matching.JobMatchingService") as mock_job_service:
        # Setup session context manager
        mock_get_session.return_value.__aenter__.return_value = mock_db_session
        mock_get_session.return_value.__aexit__.return_value = None

        # Setup mocks
        mock_user_repo_class.return_value = mock_user_repo
        mock_user_repo.get_by_telegram_id.return_value = sample_user
        mock_job_service.return_value.match_jobs_for_user.return_value = []

        try:
            # Execute
            await bot._jobs_command(mock_update, mock_context)

            # Assert
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=mock_update.effective_chat.id,
                text="No matching jobs found. Try updating your profile with more information."
            )
        finally:
            # Ensure session is cleaned up
            await mock_db_session.close()


@pytest.mark.asyncio
async def test_jobs_command_invalid_user_id(
    mock_update: MagicMock,
    mock_context: MagicMock,
    mock_db_session: AsyncMock,
):
    """Test /jobs command with invalid user ID."""
    # Setup
    bot = JobMatchingBot()
    mock_update.effective_user = None

    try:
        # Execute
        await bot._jobs_command(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=mock_update.effective_chat.id,
            text="⚠️ Could not identify user. Please try again."
        )
    finally:
        # Ensure session is cleaned up
        await mock_db_session.close()
