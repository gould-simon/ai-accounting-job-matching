"""Base service class for standardizing service lifecycle management."""
import abc
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceError
from app.database import async_session_factory

logger = logging.getLogger(__name__)


class BaseService(abc.ABC):
    """Base class for all services."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        """Initialize service.
        
        Args:
            session: Optional database session. If not provided,
                    one will be created during init()
        """
        self.session = session
        self.initialized = False
        self.last_health_check: Optional[datetime] = None
        self.name = self.__class__.__name__

    async def init(self) -> None:
        """Initialize service with required resources."""
        try:
            if not self.session:
                self.session = async_session_factory()

            await self._init_resources()
            
            self.initialized = True
            self.last_health_check = datetime.now(timezone.utc)
            
            logger.info(
                f"{self.name} initialized",
                extra={
                    "service": self.name,
                    "action": "init",
                    "status": "success"
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to initialize {self.name}",
                exc_info=e,
                extra={
                    "service": self.name,
                    "action": "init",
                    "status": "error",
                    "error": str(e)
                }
            )
            raise ServiceError(f"Failed to initialize {self.name}") from e

    async def close(self) -> None:
        """Close service and cleanup resources."""
        try:
            await self._cleanup_resources()
            
            if self.session:
                await self.session.close()
                self.session = None
                
            self.initialized = False
            
            logger.info(
                f"{self.name} closed",
                extra={
                    "service": self.name,
                    "action": "close",
                    "status": "success"
                }
            )
            
        except Exception as e:
            logger.error(
                f"Error closing {self.name}",
                exc_info=e,
                extra={
                    "service": self.name,
                    "action": "close",
                    "status": "error",
                    "error": str(e)
                }
            )
            raise ServiceError(f"Failed to close {self.name}") from e

    async def health_check(self) -> bool:
        """Check if service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            if not self.initialized:
                return False
                
            is_healthy = await self._check_health()
            
            if is_healthy:
                self.last_health_check = datetime.now(timezone.utc)
                
            return is_healthy
            
        except Exception as e:
            logger.error(
                f"Health check failed for {self.name}",
                exc_info=e,
                extra={
                    "service": self.name,
                    "action": "health_check",
                    "status": "error",
                    "error": str(e)
                }
            )
            return False

    @abc.abstractmethod
    async def _init_resources(self) -> None:
        """Initialize service-specific resources.
        
        This method should be implemented by each service to handle
        its specific initialization needs.
        """
        pass

    @abc.abstractmethod
    async def _cleanup_resources(self) -> None:
        """Cleanup service-specific resources.
        
        This method should be implemented by each service to handle
        its specific cleanup needs.
        """
        pass

    @abc.abstractmethod
    async def _check_health(self) -> bool:
        """Check service-specific health.
        
        This method should be implemented by each service to verify
        its specific health requirements.
        
        Returns:
            True if service-specific health check passes
        """
        pass
