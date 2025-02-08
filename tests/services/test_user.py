"""Tests for user service."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserUpdate
from app.services.user import UserService


@pytest.fixture
def user_service(db_session: AsyncSession):
    """Create user service instance."""
    return UserService(db_session)


@pytest.mark.asyncio
async def test_get_or_create_user(user_service: UserService):
    """Test getting or creating user."""
    # Create new user
    is_new, user = await user_service.get_or_create_user(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
    )
    assert is_new is True
    assert user["telegram_id"] == 123456789
    assert user["username"] == "testuser"
    
    # Get existing user
    is_new, user = await user_service.get_or_create_user(
        telegram_id=123456789,
        username="newname",  # Should not update
    )
    assert is_new is False
    assert user["telegram_id"] == 123456789
    assert user["username"] == "testuser"  # Original name


@pytest.mark.asyncio
async def test_update_user(
    user_service: UserService,
    mock_openai,
):
    """Test updating user data."""
    # Create user first
    _, user = await user_service.get_or_create_user(
        telegram_id=123456789,
    )
    
    # Update without CV
    update_data = UserUpdate(
        username="newname",
        first_name="New",
        last_name="Name",
    )
    updated = await user_service.update_user(123456789, update_data)
    assert updated is not None
    assert updated["username"] == "newname"
    assert updated["cv_embedding"] is None
    
    # Update with CV
    update_data = UserUpdate(
        cv_text="Test CV content",
    )
    updated = await user_service.update_user(123456789, update_data)
    assert updated is not None
    assert updated["cv_text"] == "Test CV content"
    assert isinstance(updated["cv_embedding"], list)
    assert len(updated["cv_embedding"]) == 1536
    
    # Update non-existent user
    updated = await user_service.update_user(999999, update_data)
    assert updated is None


@pytest.mark.asyncio
async def test_record_search(user_service: UserService):
    """Test recording user searches."""
    # Create user first
    await user_service.get_or_create_user(telegram_id=123456789)
    
    # Record search
    search = await user_service.record_search(
        telegram_id=123456789,
        search_query="audit jobs",
        structured_preferences={"location": "London"},
    )
    assert search["telegram_id"] == 123456789
    assert search["search_query"] == "audit jobs"
    assert search["structured_preferences"] == {"location": "London"}
    
    # Get recent searches
    searches = await user_service.get_recent_searches(123456789)
    assert len(searches) == 1
    assert searches[0]["search_query"] == "audit jobs"
    
    # Record more searches
    for i in range(5):
        await user_service.record_search(
            telegram_id=123456789,
            search_query=f"search {i}",
        )
    
    # Verify limit works
    searches = await user_service.get_recent_searches(
        telegram_id=123456789,
        limit=3,
    )
    assert len(searches) == 3
    assert searches[0]["search_query"] == "search 4"  # Most recent first


@pytest.mark.asyncio
async def test_conversation_history(user_service: UserService):
    """Test recording and retrieving conversation history."""
    # Create user first
    await user_service.get_or_create_user(telegram_id=123456789)
    
    # Record messages
    msg1 = await user_service.record_message(
        telegram_id=123456789,
        message="Hello bot",
        is_user=True,
    )
    assert msg1["telegram_id"] == 123456789
    assert msg1["message"] == "Hello bot"
    assert msg1["is_user"] is True
    
    msg2 = await user_service.record_message(
        telegram_id=123456789,
        message="Hi user",
        is_user=False,
    )
    assert msg2["is_user"] is False
    
    # Get conversation history
    messages = await user_service.get_conversation_history(123456789)
    assert len(messages) == 2
    assert messages[0]["message"] == "Hi user"  # Most recent first
    assert messages[1]["message"] == "Hello bot"
