"""User repository for database operations."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, desc, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.core.exceptions import DatabaseError, UserError
from app.models.user import User, UserSearch, UserConversation, JobMatch
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with User model."""
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get user by telegram_id {telegram_id}",
                context={"telegram_id": telegram_id},
                original_error=e
            )

    async def get_with_searches(self, user_id: int) -> Optional[User]:
        """Get user with their search history.
        
        Args:
            user_id: User ID
            
        Returns:
            User with loaded searches if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(User)
                .options(selectinload(User.searches))
                .where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get user with searches {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        """Create new user.
        
        Args:
            telegram_id: Telegram user ID
            username: Optional Telegram username
            first_name: Optional user's first name
            last_name: Optional user's last name
            
        Returns:
            Created user
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            now = datetime.now(timezone.utc)
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                created_at=now,
                updated_at=now,
            )
            self.session.add(user)
            await self.session.commit()
            return user
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create user {telegram_id}",
                context={
                    "telegram_id": telegram_id,
                    "username": username
                },
                original_error=e
            )

    async def update_cv(
        self,
        user_id: int,
        cv_text: str,
        cv_embedding: List[float]
    ) -> User:
        """Update user's CV and embedding.
        
        Args:
            user_id: User ID
            cv_text: Extracted CV text
            cv_embedding: CV text embedding vector
            
        Returns:
            Updated user
            
        Raises:
            UserError: If user not found
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                raise UserError(
                    message=f"User {user_id} not found",
                    telegram_id=user_id
                )

            user.cv_text = cv_text
            user.cv_embedding = cv_embedding
            user.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return user
        except UserError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update CV for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def update_preferences(
        self,
        user_id: int,
        preferences: Dict
    ) -> User:
        """Update user's job preferences.
        
        Args:
            user_id: User ID
            preferences: Job preferences dictionary
            
        Returns:
            Updated user
            
        Raises:
            UserError: If user not found
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                raise UserError(
                    message=f"User {user_id} not found",
                    telegram_id=user_id
                )

            user.preferences = preferences
            user.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return user
        except UserError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update preferences for user {user_id}",
                context={
                    "user_id": user_id,
                    "preferences": preferences
                },
                original_error=e
            )

    async def update_last_active(self, user_id: int) -> None:
        """Update user's last active timestamp.
        
        Args:
            user_id: User ID
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if user:
                user.last_active = datetime.now(timezone.utc)
                await self.session.commit()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update last_active for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def get_users_for_job_matching(
        self,
        *,
        min_days_since_match: int = 1,
        limit: int = 100
    ) -> List[User]:
        """Get users eligible for job matching.
        
        Args:
            min_days_since_match: Minimum days since last job match
            limit: Maximum number of users to return
            
        Returns:
            List of users eligible for job matching
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=min_days_since_match)
            result = await self.session.execute(
                select(User)
                .where(User.cv_embedding.isnot(None))
                .where(
                    ~exists().where(
                        and_(
                            JobMatch.user_id == User.id,
                            JobMatch.created_at >= cutoff
                        )
                    )
                )
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(
                message="Failed to get users for job matching",
                context={
                    "min_days_since_match": min_days_since_match,
                    "limit": limit
                },
                original_error=e
            )

    async def get_job_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user's job preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Job preferences if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                return None
            return user.job_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get job preferences for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def update_job_preferences(
        self,
        user_id: int,
        preferences: Dict
    ) -> Dict:
        """Update user's job preferences.
        
        Args:
            user_id: User ID
            preferences: New job preferences
            
        Returns:
            Updated job preferences
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                raise UserError(f"User {user_id} not found")
                
            user.job_preferences = preferences
            user.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            
            return user.job_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update job preferences for user {user_id}",
                context={"user_id": user_id, "preferences": preferences},
                original_error=e
            )

    async def get_notification_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user's notification preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Notification preferences if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                return None
            return user.notification_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get notification preferences for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def update_notification_preferences(
        self,
        user_id: int,
        preferences: Dict
    ) -> Dict:
        """Update user's notification preferences.
        
        Args:
            user_id: User ID
            preferences: New notification preferences
            
        Returns:
            Updated notification preferences
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                raise UserError(f"User {user_id} not found")
                
            user.notification_preferences = preferences
            user.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            
            return user.notification_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update notification preferences for user {user_id}",
                context={"user_id": user_id, "preferences": preferences},
                original_error=e
            )

    async def get_search_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user's search preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Search preferences if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                return None
            return user.search_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get search preferences for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def update_search_preferences(
        self,
        user_id: int,
        preferences: Dict
    ) -> Dict:
        """Update user's search preferences.
        
        Args:
            user_id: User ID
            preferences: New search preferences
            
        Returns:
            Updated search preferences
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            user = await self.get_by_telegram_id(user_id)
            if not user:
                raise UserError(f"User {user_id} not found")
                
            user.search_preferences = preferences
            user.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            
            return user.search_preferences
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update search preferences for user {user_id}",
                context={"user_id": user_id, "preferences": preferences},
                original_error=e
            )


class UserSearchRepository(BaseRepository[UserSearch]):
    """Repository for user search history operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with UserSearch model."""
        super().__init__(UserSearch, session)

    async def create_search(
        self,
        telegram_id: int,
        search_query: str,
        structured_preferences: Optional[dict] = None,
    ) -> UserSearch:
        """Create new search record.
        
        Args:
            telegram_id: Telegram user ID
            search_query: Search query text
            structured_preferences: Optional structured search preferences
            
        Returns:
            Created search record
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self.create(
                telegram_id=telegram_id,
                search_query=search_query,
                structured_preferences=structured_preferences,
                created_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create search for user {telegram_id}",
                context={
                    "telegram_id": telegram_id,
                    "search_query": search_query
                },
                original_error=e
            )

    async def get_recent_searches(
        self,
        telegram_id: int,
        limit: int = 5
    ) -> List[UserSearch]:
        """Get user's recent searches.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of searches to return
            
        Returns:
            List of recent searches
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(UserSearch)
                .where(UserSearch.telegram_id == telegram_id)
                .order_by(desc(UserSearch.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get recent searches for user {telegram_id}",
                context={
                    "telegram_id": telegram_id,
                    "limit": limit
                },
                original_error=e
            )


class UserConversationRepository(BaseRepository[UserConversation]):
    """Repository for user conversation history operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with UserConversation model."""
        super().__init__(UserConversation, session)

    async def create_message(
        self,
        telegram_id: int,
        message: str,
        is_user: bool = True,
    ) -> UserConversation:
        """Create new conversation message.
        
        Args:
            telegram_id: Telegram user ID
            message: Message content
            is_user: Whether the message is from the user (True) or bot (False)
            
        Returns:
            Created conversation record
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            return await self.create(
                telegram_id=telegram_id,
                message=message,
                is_user=is_user,
                created_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create message for user {telegram_id}",
                context={
                    "telegram_id": telegram_id,
                    "is_user": is_user
                },
                original_error=e
            )

    async def get_conversation_history(
        self,
        telegram_id: int,
        limit: int = 10,
    ) -> List[UserConversation]:
        """Get user's recent conversation history.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(UserConversation)
                .where(UserConversation.telegram_id == telegram_id)
                .order_by(desc(UserConversation.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get conversation history for user {telegram_id}",
                context={
                    "telegram_id": telegram_id,
                    "limit": limit
                },
                original_error=e
            )
