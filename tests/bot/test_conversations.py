"""Tests for Telegram bot conversations."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext, ContextTypes

from app.bot.conversations.matching import (
    start_matching,
    handle_cv_match,
    handle_job_navigation,
    show_job_details,
    handle_job_action,
    SHOWING_MATCHES,
    VIEWING_JOB
)
from app.bot.conversations.preferences import (
    start_preferences,
    handle_job_preferences,
    handle_notification_preferences,
    handle_search_preferences,
    save_preferences,
    AWAITING_PREFERENCE_TYPE,
    AWAITING_JOB_TYPE
)
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
def telegram_context():
    """Create mock Telegram context."""
    context = Mock(spec=CallbackContext)
    context.user_data = {}
    context.db_session = AsyncMock()
    return context


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
        embedding=[0.1, 0.2, 0.3],
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
        company_name="Test Company",
        location="London, UK",
        description="Looking for experienced Python developer",
        requirements="5+ years Python experience",
        salary="£60,000 - £80,000",
        status="active",
        embedding=[0.15, 0.25, 0.35],
        posted_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    await db_session.commit()
    return job


@pytest.mark.asyncio
async def test_start_matching(telegram_update, telegram_context):
    """Test starting job matching conversation."""
    # Execute
    result = await start_matching(telegram_update, telegram_context)
    
    # Verify
    assert result == AWAITING_PREFERENCE_TYPE
    telegram_update.message.reply_text.assert_called_once()
    args = telegram_update.message.reply_text.call_args[0]
    assert "How would you like to find jobs?" in args[0]


@pytest.mark.asyncio
async def test_handle_cv_match_no_cv(
    telegram_update,
    telegram_context,
    test_user
):
    """Test CV matching without uploaded CV."""
    # Setup
    telegram_update.callback_query = Mock()
    telegram_update.callback_query.message = telegram_update.message
    
    # Execute
    result = await handle_cv_match(telegram_update, telegram_context)
    
    # Verify
    assert result == -1  # ConversationHandler.END
    telegram_update.callback_query.message.reply_text.assert_called_once_with(
        "You haven't uploaded a CV yet! Use /upload_cv to upload one."
    )


@pytest.mark.asyncio
async def test_handle_cv_match_with_matches(
    telegram_update,
    telegram_context,
    test_user,
    test_cv,
    test_job
):
    """Test CV matching with matching jobs."""
    # Setup
    telegram_update.callback_query = Mock()
    telegram_update.callback_query.message = telegram_update.message
    
    # Execute
    result = await handle_cv_match(telegram_update, telegram_context)
    
    # Verify
    assert result == SHOWING_MATCHES
    assert "matches" in telegram_context.user_data
    assert telegram_context.user_data["page"] == 0
    telegram_update.callback_query.message.reply_text.assert_called_once()
    args = telegram_update.callback_query.message.reply_text.call_args[0]
    assert "Here are your matching jobs" in args[0]
    assert test_job.title in args[0]


@pytest.mark.asyncio
async def test_start_preferences(telegram_update, telegram_context):
    """Test starting preferences conversation."""
    # Execute
    result = await start_preferences(telegram_update, telegram_context)
    
    # Verify
    assert result == AWAITING_PREFERENCE_TYPE
    telegram_update.message.reply_text.assert_called_once()
    args = telegram_update.message.reply_text.call_args[0]
    assert "What preferences would you like to update?" in args[0]


@pytest.mark.asyncio
async def test_handle_job_preferences(telegram_update, telegram_context):
    """Test handling job preferences selection."""
    # Setup
    telegram_update.callback_query = Mock()
    telegram_update.callback_query.message = telegram_update.message
    
    # Execute
    result = await handle_job_preferences(telegram_update, telegram_context)
    
    # Verify
    assert result == AWAITING_JOB_TYPE
    telegram_update.callback_query.message.reply_text.assert_called_once()
    args = telegram_update.callback_query.message.reply_text.call_args[0]
    assert "Select your preferred job types" in args[0]


@pytest.mark.asyncio
async def test_save_preferences(
    telegram_update,
    telegram_context,
    test_user
):
    """Test saving user preferences."""
    # Setup
    telegram_context.user_data.update({
        "job_types": ["Full-time", "Contract"],
        "work_locations": ["Remote", "Office"],
        "notification_type": "telegram",
        "search_radius": 25
    })
    
    # Execute
    result = await save_preferences(telegram_update, telegram_context)
    
    # Verify
    assert result == -1  # ConversationHandler.END
    telegram_update.message.reply_text.assert_called_once()
    args = telegram_update.message.reply_text.call_args[0]
    assert "Your preferences have been saved!" in args[0]
    assert not telegram_context.user_data  # Should be cleared
