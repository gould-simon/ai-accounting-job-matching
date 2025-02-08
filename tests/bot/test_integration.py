"""Integration tests for Telegram bot."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from telegram import Update, User, Message, Chat, Document
from telegram.ext import Application

from app.bot.handler import JobMatchingBot
from app.models.cv import CV
from app.models.job import Job
from app.models.user import User as DbUser


@pytest.fixture
def telegram_user():
    """Create mock Telegram user."""
    return User(
        id=123456,
        first_name="Test",
        last_name="User",
        username="test_user",
        is_bot=False
    )


@pytest.fixture
def telegram_chat():
    """Create mock Telegram chat."""
    return Chat(
        id=123456,
        type="private"
    )


@pytest.fixture
def telegram_message(telegram_user, telegram_chat):
    """Create mock Telegram message."""
    message = Mock(spec=Message)
    message.from_user = telegram_user
    message.chat = telegram_chat
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def telegram_update(telegram_user, telegram_message):
    """Create mock Telegram update."""
    update = Mock(spec=Update)
    update.effective_user = telegram_user
    update.message = telegram_message
    update.callback_query = None
    return update


@pytest.fixture
async def test_user(db_session):
    """Create test database user."""
    user = DbUser(
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
async def test_jobs(db_session):
    """Create test jobs."""
    jobs = [
        Job(
            title="Senior Python Developer",
            company_name="Tech Corp",
            location="London, UK",
            description="Looking for experienced Python developer",
            requirements="5+ years Python experience",
            salary="£60,000 - £80,000",
            status="active",
            embedding=[0.1, 0.2, 0.3],
            posted_at=datetime.now(timezone.utc)
        ),
        Job(
            title="Python Backend Engineer",
            company_name="Startup Inc",
            location="Remote",
            description="Backend role with Python and FastAPI",
            requirements="3+ years Python experience",
            salary="£50,000 - £70,000",
            status="active",
            embedding=[0.15, 0.25, 0.35],
            posted_at=datetime.now(timezone.utc)
        )
    ]
    for job in jobs:
        db_session.add(job)
    await db_session.commit()
    return jobs


@pytest.mark.asyncio
async def test_bot_full_flow(
    telegram_update,
    test_user,
    test_jobs,
    tmp_path,
    monkeypatch
):
    """Test complete bot interaction flow."""
    # Setup bot
    bot = JobMatchingBot("test_token")
    
    # Mock application
    mock_app = Mock(spec=Application)
    mock_app.bot = Mock()
    mock_app.bot.get_file = AsyncMock()
    monkeypatch.setattr(bot, "application", mock_app)
    
    # 1. Test start command
    telegram_update.message.text = "/start"
    await bot.start(telegram_update, None)
    
    welcome_call = telegram_update.message.reply_text.call_args_list[0]
    assert "Welcome to the AI Accounting Job Matching Bot!" in welcome_call[0][0]
    
    # 2. Test CV upload
    # Create test PDF
    cv_path = tmp_path / "test_cv.pdf"
    cv_path.write_bytes(b"Test CV content")
    
    # Mock document
    document = Mock(spec=Document)
    document.file_name = "test_cv.pdf"
    document.mime_type = "application/pdf"
    telegram_update.message.document = document
    
    # Mock file download
    mock_file = AsyncMock()
    mock_file.download = AsyncMock(return_value=str(cv_path))
    mock_app.bot.get_file.return_value = mock_file
    
    await bot.process_cv(telegram_update, None)
    
    cv_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "CV uploaded successfully" in cv_call[0][0]
    
    # 3. Test preferences update
    telegram_update.message.text = "/preferences"
    result = await bot.start_preferences(telegram_update, None)
    
    prefs_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "What preferences would you like to update?" in prefs_call[0][0]
    
    # 4. Test job search
    telegram_update.message.text = "/search"
    result = await bot.start_search(telegram_update, None)
    
    search_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "Enter keywords to search for jobs" in search_call[0][0]
    
    # Simulate search query
    telegram_update.message.text = "python developer"
    await bot.handle_search_query(telegram_update, None)
    
    results_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "Here are the matching jobs" in results_call[0][0]
    assert "Senior Python Developer" in results_call[0][0]
    
    # 5. Test job matching
    telegram_update.message.text = "/matches"
    result = await bot.start_matching(telegram_update, None)
    
    match_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "How would you like to find jobs?" in match_call[0][0]
    
    # Simulate CV match selection
    telegram_update.callback_query = Mock()
    telegram_update.callback_query.data = "cv_match"
    telegram_update.callback_query.message = telegram_update.message
    
    await bot.handle_cv_match(telegram_update, None)
    
    matches_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "Here are your matching jobs" in matches_call[0][0]
    
    # 6. Test help command
    telegram_update.message.text = "/help"
    await bot.help(telegram_update, None)
    
    help_call = telegram_update.message.reply_text.call_args_list[-1]
    assert "Available commands" in help_call[0][0]
