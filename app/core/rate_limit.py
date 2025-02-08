"""Rate limiting implementation."""
import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

import redis
from redis.asyncio import Redis
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RateLimitInfo:
    """Rate limit information."""

    remaining: int
    reset_at: datetime
    total: int


class RateLimiter:
    """Base rate limiter implementation."""

    def __init__(
        self,
        redis_url: str,
        key_prefix: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Initialize rate limiter.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
            max_requests: Maximum requests per window
            window_seconds: Window size in seconds
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis: Optional[Redis] = None

    async def init(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis", extra={"url": self.redis_url})
        except Exception as e:
            logger.error("Failed to connect to Redis", exc_info=e)
            raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Closed Redis connection")

    def _get_key(self, identifier: str) -> str:
        """Get Redis key for identifier.

        Args:
            identifier: Rate limit identifier

        Returns:
            Redis key
        """
        return f"{self.key_prefix}:{identifier}"

    async def get_limit_info(self, identifier: str) -> RateLimitInfo:
        """Get rate limit information.

        Args:
            identifier: Rate limit identifier

        Returns:
            Rate limit information

        Raises:
            RateLimitError: If Redis is not initialized
        """
        if not self.redis:
            raise RateLimitError("Rate limiter not initialized")

        key = self._get_key(identifier)
        now = time.time()
        window_start = int(now - (now % self.window_seconds))

        # Get current count and expiry
        count = await self.redis.get(key)
        ttl = await self.redis.ttl(key)

        if count is None:
            # No requests in current window
            return RateLimitInfo(
                remaining=self.max_requests,
                reset_at=datetime.fromtimestamp(window_start + self.window_seconds),
                total=self.max_requests,
            )

        count = int(count)
        return RateLimitInfo(
            remaining=max(0, self.max_requests - count),
            reset_at=datetime.fromtimestamp(window_start + self.window_seconds),
            total=self.max_requests,
        )

    async def acquire(self, identifier: str) -> None:
        """Acquire rate limit token.

        Args:
            identifier: Rate limit identifier

        Raises:
            RateLimitError: If rate limit exceeded or Redis error
        """
        if not self.redis:
            raise RateLimitError("Rate limiter not initialized")

        key = self._get_key(identifier)
        now = time.time()
        window_start = int(now - (now % self.window_seconds))

        try:
            # Increment counter and set expiry
            count = await self.redis.incr(key)
            if count == 1:
                # Set expiry for new keys
                await self.redis.expireat(key, window_start + self.window_seconds)

            if count > self.max_requests:
                # Rate limit exceeded
                info = await self.get_limit_info(identifier)
                raise RateLimitError(
                    f"Rate limit exceeded. Reset in {info.reset_at - datetime.now()}"
                )

        except redis.RedisError as e:
            logger.error("Redis error", exc_info=e)
            raise RateLimitError("Failed to check rate limit") from e

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorate function with rate limiting.

        Args:
            func: Function to decorate

        Returns:
            Decorated function
        """

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get identifier from function name
            identifier = func.__name__

            try:
                await self.acquire(identifier)
                return await func(*args, **kwargs)
            except RateLimitError:
                raise
            except Exception as e:
                logger.error("Error in rate limited function", exc_info=e)
                raise

        return wrapper


class OpenAIRateLimiter(RateLimiter):
    """Rate limiter for OpenAI API."""

    def __init__(self) -> None:
        """Initialize OpenAI rate limiter."""
        super().__init__(
            redis_url=settings.REDIS_URL,
            key_prefix="openai",
            max_requests=settings.OPENAI_RATE_LIMIT_RPM,
            window_seconds=60,
        )


# Global rate limiter instances
openai_rate_limiter = OpenAIRateLimiter()
