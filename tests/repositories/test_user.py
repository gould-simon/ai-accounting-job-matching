"""Tests for user repository."""
import pytest
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError, UserError
from app.models.user import User, UserSearch, UserConversation
from app.repositories.user import (
    UserRepository,
    UserSearchRepository,
    UserConversationRepository
)


@pytest.fixture
async def user_repo(db_session: AsyncSession) -> UserRepository:
    """Create user repository."""
    return UserRepository(db_session)


@pytest.fixture
async def search_repo(db_session: AsyncSession) -> UserSearchRepository:
    """Create user search repository."""
    return UserSearchRepository(db_session)


@pytest.fixture
async def conversation_repo(db_session: AsyncSession) -> UserConversationRepository:
    """Create user conversation repository."""
    return UserConversationRepository(db_session)


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


@pytest.mark.asyncio
async def test_create_user(user_repo: UserRepository):
    """Test user creation."""
    user = await user_repo.create_user(
        telegram_id=987654321,
        username="newuser",
        first_name="New",
        last_name="User"
    )
    
    assert user.telegram_id == 987654321
    assert user.username == "newuser"
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_get_by_telegram_id(
    user_repo: UserRepository,
    sample_user: User
):
    """Test getting user by Telegram ID."""
    user = await user_repo.get_by_telegram_id(sample_user.telegram_id)
    assert user is not None
    assert user.telegram_id == sample_user.telegram_id
    assert user.username == sample_user.username

    # Test non-existent user
    user = await user_repo.get_by_telegram_id(999999)
    assert user is None


@pytest.mark.asyncio
async def test_update_cv(
    user_repo: UserRepository,
    sample_user: User
):
    """Test updating user CV."""
    cv_text = "Sample CV text"
    cv_embedding = [0.1] * 1536

    updated_user = await user_repo.update_cv(
        sample_user.id,
        cv_text,
        cv_embedding
    )
    
    assert updated_user.cv_text == cv_text
    assert updated_user.cv_embedding == cv_embedding
    assert updated_user.updated_at > sample_user.updated_at

    # Test non-existent user
    with pytest.raises(UserError):
        await user_repo.update_cv(999, cv_text, cv_embedding)


@pytest.mark.asyncio
async def test_update_preferences(
    user_repo: UserRepository,
    sample_user: User
):
    """Test updating user preferences."""
    preferences = {
        "location": "London",
        "salary_min": 50000,
        "job_type": "Full-time"
    }

    updated_user = await user_repo.update_preferences(
        sample_user.id,
        preferences
    )
    
    assert updated_user.preferences == preferences
    assert updated_user.updated_at > sample_user.updated_at

    # Test non-existent user
    with pytest.raises(UserError):
        await user_repo.update_preferences(999, preferences)


@pytest.mark.asyncio
async def test_update_last_active(
    user_repo: UserRepository,
    sample_user: User
):
    """Test updating last active timestamp."""
    old_last_active = sample_user.last_active
    await user_repo.update_last_active(sample_user.id)
    
    updated_user = await user_repo.get(sample_user.id)
    assert updated_user.last_active > old_last_active


@pytest.mark.asyncio
async def test_create_search(
    search_repo: UserSearchRepository,
    sample_user: User
):
    """Test creating user search."""
    search = await search_repo.create_search(
        telegram_id=sample_user.telegram_id,
        search_query="accounting jobs in London",
        structured_preferences={
            "location": "London",
            "role": "accountant"
        }
    )
    
    assert search.telegram_id == sample_user.telegram_id
    assert search.search_query == "accounting jobs in London"
    assert search.structured_preferences == {
        "location": "London",
        "role": "accountant"
    }
    assert search.created_at is not None


@pytest.mark.asyncio
async def test_get_recent_searches(
    search_repo: UserSearchRepository,
    sample_user: User
):
    """Test getting recent searches."""
    # Create multiple searches
    searches = []
    for i in range(3):
        search = await search_repo.create_search(
            telegram_id=sample_user.telegram_id,
            search_query=f"search query {i}"
        )
        searches.append(search)

    recent_searches = await search_repo.get_recent_searches(
        sample_user.telegram_id,
        limit=2
    )
    
    assert len(recent_searches) == 2
    assert recent_searches[0].search_query == "search query 2"
    assert recent_searches[1].search_query == "search query 1"


@pytest.mark.asyncio
async def test_create_conversation_message(
    conversation_repo: UserConversationRepository,
    sample_user: User
):
    """Test creating conversation message."""
    message = await conversation_repo.create_message(
        telegram_id=sample_user.telegram_id,
        message="Hello bot!",
        is_user=True
    )
    
    assert message.telegram_id == sample_user.telegram_id
    assert message.message == "Hello bot!"
    assert message.is_user is True
    assert message.created_at is not None


@pytest.mark.asyncio
async def test_get_conversation_history(
    conversation_repo: UserConversationRepository,
    sample_user: User
):
    """Test getting conversation history."""
    # Create multiple messages
    messages = []
    for i in range(3):
        message = await conversation_repo.create_message(
            telegram_id=sample_user.telegram_id,
            message=f"message {i}",
            is_user=i % 2 == 0
        )
        messages.append(message)

    history = await conversation_repo.get_conversation_history(
        sample_user.telegram_id,
        limit=2
    )
    
    assert len(history) == 2
    assert history[0].message == "message 2"
    assert history[1].message == "message 1"
    assert history[0].is_user is True
    assert history[1].is_user is False
