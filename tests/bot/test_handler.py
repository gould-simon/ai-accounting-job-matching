"""Tests for Telegram bot handler."""
import pytest
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.handler import JobMatchingBot
from app.models.cv import CV
from app.models.job import Job
from app.models.user import User


@pytest.fixture
def bot(db_session):
    """Create test bot instance."""
    bot = JobMatchingBot("test_token")
    bot.application.bot_data["db"] = db_session
    return bot


@pytest.fixture
def mock_update():
    """Create mock update."""
    update = Update.de_json({
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": 1612345678,
            "chat": {
                "id": 123456789,
                "type": "private",
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User"
            },
            "from": {
                "id": 123456789,
                "is_bot": False,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "en"
            },
            "text": "/start"
        }
    }, bot=None)
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = ContextTypes.DEFAULT_TYPE()
    context.bot_data = {}
    context.user_data = {}
    context.chat_data = {}
    return context


@pytest.mark.asyncio
async def test_start_command_new_user(
    bot,
    mock_update,
    mock_context,
    db_session
):
    """Test /start command for new user."""
    # Setup
    mock_context.bot_data["db"] = db_session

    # Execute
    await bot.start(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Welcome Test!" in text
    assert "/upload_cv" in text
    assert "/search" in text
    assert "/preferences" in text

    # Check user was created
    user = await db_session.get(User, mock_update.effective_user.id)
    assert user is not None
    assert user.telegram_id == mock_update.effective_user.id
    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.last_name == "User"


@pytest.mark.asyncio
async def test_start_command_existing_user(
    bot,
    mock_update,
    mock_context,
    db_session
):
    """Test /start command for existing user."""
    # Setup
    mock_context.bot_data["db"] = db_session
    user = User(
        telegram_id=mock_update.effective_user.id,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    db_session.add(user)
    await db_session.commit()

    # Execute
    await bot.start(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Welcome Test!" in text

    # Check user wasn't duplicated
    users = await db_session.query(User).all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_help_command(bot, mock_update, mock_context):
    """Test /help command."""
    # Execute
    await bot.help(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Available Commands" in text
    assert "/upload_cv" in text
    assert "/search" in text
    assert "/preferences" in text


@pytest.mark.asyncio
async def test_start_cv_upload(bot, mock_update, mock_context):
    """Test starting CV upload conversation."""
    # Execute
    result = await bot.start_cv_upload(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Please send me your CV" in text
    assert result == bot.AWAITING_CV


@pytest.mark.asyncio
async def test_process_cv_invalid_type(
    bot,
    mock_update,
    mock_context
):
    """Test CV upload with invalid file type."""
    # Setup
    mock_update.message.document.mime_type = "text/plain"
    mock_update.message.document.file_name = "test.txt"

    # Execute
    result = await bot.process_cv(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "only process PDF and DOCX files" in text
    assert result == bot.AWAITING_CV


@pytest.mark.asyncio
async def test_start_search(bot, mock_update, mock_context):
    """Test starting job search conversation."""
    # Execute
    result = await bot.start_search(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Let's find your perfect accounting job" in text
    assert result == bot.AWAITING_SEARCH_QUERY


@pytest.mark.asyncio
async def test_handle_search_query_no_results(
    bot,
    mock_update,
    mock_context,
    db_session
):
    """Test job search with no results."""
    # Setup
    mock_context.bot_data["db"] = db_session
    mock_update.message.text = "Non-existent job"

    # Execute
    result = await bot.handle_search_query(mock_update, mock_context)

    # Verify
    text = mock_update.message.reply_text.call_args[0][0]
    assert "No jobs found" in text
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_cancel(bot, mock_update, mock_context):
    """Test cancelling conversation."""
    # Execute
    result = await bot.cancel(mock_update, mock_context)

    # Verify
    assert mock_update.message.reply_text.call_count == 1
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Operation cancelled" in text
    assert result == ConversationHandler.END
