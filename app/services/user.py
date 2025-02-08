"""Service for user-related operations."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import (
    UserConversationRepository,
    UserRepository,
    UserSearchRepository,
)
from app.schemas.user import UserCreate, UserUpdate
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user data and operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repositories.
        
        Args:
            session: Database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.search_repo = UserSearchRepository(session)
        self.conversation_repo = UserConversationRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        **user_data: str,
    ) -> tuple[bool, dict]:
        """Get existing user or create new one.
        
        Args:
            telegram_id: Telegram user ID
            **user_data: Additional user data
            
        Returns:
            Tuple of (is_new, user_dict)
        """
        # Check if user exists
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            return False, user.to_dict()
            
        # Create new user
        user_in = UserCreate(
            telegram_id=telegram_id,
            **user_data,
        )
        user = await self.user_repo.create_user(
            telegram_id=user_in.telegram_id,
            username=user_in.username,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
        )
        return True, user.to_dict()

    async def update_user(
        self,
        telegram_id: int,
        update_data: UserUpdate,
    ) -> Optional[dict]:
        """Update user data.
        
        Args:
            telegram_id: Telegram user ID
            update_data: Data to update
            
        Returns:
            Updated user dict if found
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None
            
        # Generate embedding if CV text provided
        if update_data.cv_text:
            cv_embedding = await embedding_service.create_embedding(
                update_data.cv_text
            )
            update_data_dict = update_data.model_dump()
            update_data_dict["cv_embedding"] = cv_embedding
        else:
            update_data_dict = update_data.model_dump()
            
        # Update user
        user = await self.user_repo.update(
            user,
            updated_at=datetime.now(timezone.utc),
            **update_data_dict,
        )
        return user.to_dict()

    async def record_search(
        self,
        telegram_id: int,
        search_query: str,
        structured_preferences: Optional[dict] = None,
    ) -> dict:
        """Record user search.
        
        Args:
            telegram_id: Telegram user ID
            search_query: Search query text
            structured_preferences: Optional structured preferences
            
        Returns:
            Created search record
        """
        search = await self.search_repo.create_search(
            telegram_id=telegram_id,
            search_query=search_query,
            structured_preferences=structured_preferences,
        )
        return search.to_dict()

    async def get_recent_searches(
        self,
        telegram_id: int,
        limit: int = 5,
    ) -> list[dict]:
        """Get user's recent searches.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of searches
            
        Returns:
            List of search records
        """
        searches = await self.search_repo.get_user_searches(
            telegram_id=telegram_id,
            limit=limit,
        )
        return [s.to_dict() for s in searches]

    async def record_message(
        self,
        telegram_id: int,
        message: str,
        is_user: bool = True,
    ) -> dict:
        """Record conversation message.
        
        Args:
            telegram_id: Telegram user ID
            message: Message content
            is_user: Whether message is from user
            
        Returns:
            Created message record
        """
        msg = await self.conversation_repo.create_message(
            telegram_id=telegram_id,
            message=message,
            is_user=is_user,
        )
        return msg.to_dict()

    async def get_conversation_history(
        self,
        telegram_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """Get user's conversation history.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of messages
            
        Returns:
            List of conversation messages
        """
        messages = await self.conversation_repo.get_conversation_history(
            telegram_id=telegram_id,
            limit=limit,
        )
        return [m.to_dict() for m in messages]
