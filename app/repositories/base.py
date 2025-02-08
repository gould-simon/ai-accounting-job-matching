"""Base repository class for database operations."""
import logging
from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Select

from app.models.base import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            session: SQLAlchemy async session
        """
        self.model = model
        self.session = session

    async def get(self, id: Any) -> Optional[ModelType]:
        """Get model by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance if found, None otherwise
        """
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "Error getting %s with id %s: %s",
                self.model.__name__,
                id,
                str(e),
            )
            raise

    async def get_by_attribute(
        self, 
        attr: str, 
        value: Any,
    ) -> Optional[ModelType]:
        """Get model by attribute value.
        
        Args:
            attr: Model attribute name
            value: Attribute value to match
            
        Returns:
            Model instance if found, None otherwise
        """
        try:
            result = await self.session.execute(
                select(self.model).where(getattr(self.model, attr) == value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "Error getting %s with %s=%s: %s",
                self.model.__name__,
                attr,
                value,
                str(e),
            )
            raise

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        query: Optional[Select] = None,
    ) -> list[ModelType]:
        """Get list of models with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            query: Optional custom query to execute
            
        Returns:
            List of model instances
        """
        try:
            if query is None:
                query = select(self.model)
            
            result = await self.session.execute(
                query.offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                "Error listing %s (skip=%d, limit=%d): %s",
                self.model.__name__,
                skip,
                limit,
                str(e),
            )
            raise

    async def create(self, **kwargs: Any) -> ModelType:
        """Create new model instance.
        
        Args:
            **kwargs: Model attribute values
            
        Returns:
            Created model instance
        """
        try:
            db_obj = self.model(**kwargs)
            self.session.add(db_obj)
            await self.session.flush()
            return db_obj
        except Exception as e:
            logger.error(
                "Error creating %s: %s",
                self.model.__name__,
                str(e),
            )
            raise

    async def update(
        self,
        db_obj: ModelType,
        **kwargs: Any,
    ) -> ModelType:
        """Update model instance.
        
        Args:
            db_obj: Model instance to update
            **kwargs: New attribute values
            
        Returns:
            Updated model instance
        """
        try:
            for key, value in kwargs.items():
                setattr(db_obj, key, value)
            await self.session.flush()
            return db_obj
        except Exception as e:
            logger.error(
                "Error updating %s (id=%s): %s",
                self.model.__name__,
                getattr(db_obj, "id", None),
                str(e),
            )
            raise

    async def delete(self, db_obj: ModelType) -> None:
        """Delete model instance.
        
        Args:
            db_obj: Model instance to delete
        """
        try:
            await self.session.delete(db_obj)
            await self.session.flush()
        except Exception as e:
            logger.error(
                "Error deleting %s (id=%s): %s",
                self.model.__name__,
                getattr(db_obj, "id", None),
                str(e),
            )
            raise
