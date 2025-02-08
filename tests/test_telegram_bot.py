"""Tests for Telegram bot functionality."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from app.telegram_bot import JobMatchingBot
from app.core.config import settings
from app.models.user import User as DBUser
from app.repositories.user import UserRepository


@pytest.fixture
def bot():
    """Create a bot instance for testing."""
    return JobMatchingBot()


@pytest.fixture
def mock_update():
    """Create a mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.effective_user.first_name = "Test"
    
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    
    update.message = MagicMock(spec=Message)
    update.message.text = "/jobs"
    update.message.chat = update.effective_chat
    update.message.reply_text = AsyncMock()
    
    update.effective_message = update.message
    return update


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.mark.asyncio
async def test_bot_initialization(bot):
    """Test bot initialization."""
    await bot.init()
    assert bot._setup_done
    assert bot.application is not None


@pytest.mark.asyncio
async def test_start_command(bot, mock_update, mock_context):
    """Test /start command."""
    await bot._start_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    args, _ = mock_update.effective_message.reply_text.call_args
    welcome_text = args[0]
    assert "Welcome" in welcome_text
    assert "/jobs" in welcome_text


@pytest.mark.asyncio
async def test_jobs_command_no_user(bot, mock_update, mock_context):
    """Test /jobs command when user not in database."""
    with patch("app.repositories.user.UserRepository.get_by_telegram_id", return_value=None):
        await bot._jobs_command(mock_update, mock_context)
        mock_update.effective_message.reply_text.assert_called_once()
        args, _ = mock_update.effective_message.reply_text.call_args
        error_text = args[0]
        assert "CV" in error_text


@pytest.mark.asyncio
async def test_jobs_command_with_user_no_cv(bot, mock_update, mock_context):
    """Test /jobs command when user exists but has no CV."""
    mock_user = DBUser(
        telegram_id=12345,
        username="test_user",
        first_name="Test",
        cv_text=None,
        cv_embedding=None
    )
    
    with patch("app.repositories.user.UserRepository.get_by_telegram_id", return_value=mock_user):
        await bot._jobs_command(mock_update, mock_context)
        mock_update.effective_message.reply_text.assert_called_once()
        args, _ = mock_update.effective_message.reply_text.call_args
        error_text = args[0]
        assert "CV" in error_text


@pytest.mark.asyncio
async def test_jobs_command_with_user_and_cv(bot, mock_update, mock_context):
    """Test /jobs command when user exists and has CV."""
    mock_user = DBUser(
        telegram_id=12345,
        username="test_user",
        first_name="Test",
        cv_text="Sample CV",
        cv_embedding=[0.1, 0.2, 0.3]
    )
    
    mock_matches = [
        (MagicMock(
            id=1,
            title="Test Job",
            company="Test Company",
            location="Test Location",
            seniority="Senior",
            service="Audit",
            salary="100k",
            description="Test Description"
        ), 0.95)
    ]
    
    with patch("app.repositories.user.UserRepository.get_by_telegram_id", return_value=mock_user), \
         patch("app.services.job_matching.JobMatchingService.match_jobs_for_user", return_value=mock_matches):
        await bot._jobs_command(mock_update, mock_context)
        assert mock_update.effective_message.reply_text.call_count >= 1
        # Check that job details were sent
        calls = mock_update.effective_message.reply_text.call_args_list
        job_text = calls[0][0][0]
        assert "Test Job" in job_text
        assert "Test Company" in job_text


@pytest.mark.asyncio
async def test_error_handler(bot, mock_update, mock_context):
    """Test error handling."""
    mock_context.error = Exception("Test error")
    await bot._error_handler(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    args, _ = mock_update.effective_message.reply_text.call_args
    error_text = args[0]
    assert "error" in error_text.lower()


@pytest.mark.asyncio
async def test_debug_updates(bot, mock_update, mock_context):
    """Test debug update logging."""
    await bot.debug_updates(mock_update, mock_context)
    # This test mainly ensures the debug handler doesn't raise exceptions
    # Actual logging would be tested with a mock logger
