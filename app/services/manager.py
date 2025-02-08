"""Service manager for handling service lifecycle."""
import asyncio
import logging
from typing import Dict, List, Optional, Type

from app.core.config import settings
from app.services.base import BaseService
from app.services.embeddings import EmbeddingService, embedding_service
from app.services.job_matching import JobMatchingService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manager for handling service lifecycle."""

    def __init__(self) -> None:
        """Initialize service manager."""
        self.services: Dict[str, BaseService] = {}
        self.health_check_interval = settings.HEALTH_CHECK_INTERVAL
        self._health_check_task: Optional[asyncio.Task] = None

    async def init_services(self) -> None:
        """Initialize all required services."""
        services_to_init = [
            embedding_service,
            JobMatchingService(),
        ]

        for service in services_to_init:
            service_name = service.__class__.__name__
            try:
                await service.init()
                self.services[service_name] = service
                logger.info(
                    f"Initialized {service_name}",
                    extra={
                        "service": service_name,
                        "action": "init",
                        "status": "success"
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize {service_name}",
                    exc_info=e,
                    extra={
                        "service": service_name,
                        "action": "init",
                        "status": "error",
                        "error": str(e)
                    }
                )
                # Continue initializing other services
                continue

        # Start health check loop
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def close_services(self) -> None:
        """Close all services."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        for service_name, service in self.services.items():
            try:
                await service.close()
                logger.info(
                    f"Closed {service_name}",
                    extra={
                        "service": service_name,
                        "action": "close",
                        "status": "success"
                    }
                )
            except Exception as e:
                logger.error(
                    f"Error closing {service_name}",
                    exc_info=e,
                    extra={
                        "service": service_name,
                        "action": "close",
                        "status": "error",
                        "error": str(e)
                    }
                )

        self.services.clear()

    async def _health_check_loop(self) -> None:
        """Run periodic health checks on all services."""
        while True:
            try:
                unhealthy_services = []
                
                for service_name, service in self.services.items():
                    try:
                        is_healthy = await service.health_check()
                        if not is_healthy:
                            unhealthy_services.append(service_name)
                            
                    except Exception as e:
                        logger.error(
                            f"Health check failed for {service_name}",
                            exc_info=e,
                            extra={
                                "service": service_name,
                                "action": "health_check",
                                "status": "error",
                                "error": str(e)
                            }
                        )
                        unhealthy_services.append(service_name)

                if unhealthy_services:
                    logger.warning(
                        "Unhealthy services detected",
                        extra={
                            "unhealthy_services": unhealthy_services
                        }
                    )
                    
                    # Try to reinitialize unhealthy services
                    for service_name in unhealthy_services:
                        service = self.services[service_name]
                        try:
                            await service.close()
                            await service.init()
                            logger.info(
                                f"Reinitialized {service_name}",
                                extra={
                                    "service": service_name,
                                    "action": "reinit",
                                    "status": "success"
                                }
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to reinitialize {service_name}",
                                exc_info=e,
                                extra={
                                    "service": service_name,
                                    "action": "reinit",
                                    "status": "error",
                                    "error": str(e)
                                }
                            )

            except Exception as e:
                logger.error(
                    "Error in health check loop",
                    exc_info=e
                )

            await asyncio.sleep(self.health_check_interval)

    def get_service(self, service_type: Type[BaseService]) -> Optional[BaseService]:
        """Get service by type.
        
        Args:
            service_type: Type of service to get
            
        Returns:
            Service instance if found, None otherwise
        """
        service_name = service_type.__name__
        return self.services.get(service_name)


# Global service manager instance
service_manager = ServiceManager()
