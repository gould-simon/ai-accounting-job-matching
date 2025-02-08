"""Tests for rate limiting functionality."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from app.core.exceptions import RateLimitError
from app.core.rate_limit import (
    OpenAIRateLimiter,
    RateLimit,
    RateLimiter,
    rate_limit,
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock(spec=redis.Redis)
    mock.pipeline.return_value.__aenter__.return_value = AsyncMock()
    return mock


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis."""
    limiter = RateLimiter()
    limiter.redis = mock_redis
    limiter.enabled = True
    return limiter


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.client.host = "127.0.0.1"
    request.state.user_id = 123
    request.url.path = "/test"
    return request


@pytest.mark.asyncio
async def test_rate_limiter_basic(rate_limiter, mock_redis):
    """Test basic rate limiting functionality."""
    rate_limit = RateLimit(
        key="test",
        limit=5,
        window=60,
        error_msg="Test limit exceeded"
    )

    # Mock Redis pipeline execution
    pipeline = mock_redis.pipeline.return_value.__aenter__.return_value
    pipeline.execute.return_value = [None, None, 3, None]  # 3 requests made

    is_limited, info = await rate_limiter.is_rate_limited(
        rate_limit,
        "test_user"
    )

    assert not is_limited
    assert info["limit"] == 5
    assert info["remaining"] == 2
    assert "reset" in info
    assert info["window"] == 60


@pytest.mark.asyncio
async def test_rate_limiter_exceeded(rate_limiter, mock_redis):
    """Test rate limit exceeded."""
    rate_limit = RateLimit(
        key="test",
        limit=5,
        window=60
    )

    # Mock Redis pipeline execution
    pipeline = mock_redis.pipeline.return_value.__aenter__.return_value
    pipeline.execute.return_value = [None, None, 6, None]  # 6 requests made

    is_limited, info = await rate_limiter.is_rate_limited(
        rate_limit,
        "test_user"
    )

    assert is_limited
    assert info["remaining"] == 0


@pytest.mark.asyncio
async def test_rate_limiter_redis_error(rate_limiter, mock_redis):
    """Test handling of Redis errors."""
    rate_limit = RateLimit(
        key="test",
        limit=5,
        window=60
    )

    # Simulate Redis error
    mock_redis.pipeline.side_effect = redis.RedisError("Test error")

    is_limited, info = await rate_limiter.is_rate_limited(
        rate_limit,
        "test_user"
    )

    assert not is_limited  # Allow request on Redis error
    assert not info  # Empty info on error


@pytest.mark.asyncio
async def test_rate_limit_decorator():
    """Test rate limit decorator."""
    app = FastAPI()

    @app.get("/test")
    @rate_limit(limit=5, window=60)
    async def test_endpoint(request: Request):
        return {"message": "success"}

    with patch("app.core.rate_limit.rate_limiter") as mock_limiter:
        # Mock rate limiter response
        mock_limiter.is_rate_limited.return_value = (False, {
            "limit": 5,
            "remaining": 4,
            "reset": datetime.now(timezone.utc).isoformat(),
            "window": 60
        })

        # Create test client
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test successful request
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_decorator_exceeded():
    """Test rate limit decorator when limit exceeded."""
    app = FastAPI()

    @app.get("/test")
    @rate_limit(limit=5, window=60, error_msg="Custom error")
    async def test_endpoint(request: Request):
        return {"message": "success"}

    with patch("app.core.rate_limit.rate_limiter") as mock_limiter:
        # Mock rate limiter response
        mock_limiter.is_rate_limited.return_value = (True, {
            "limit": 5,
            "remaining": 0,
            "reset": datetime.now(timezone.utc).isoformat(),
            "window": 60
        })

        # Create test client
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test rate limited request
        response = client.get("/test")
        assert response.status_code == 429
        assert "Custom error" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_openai_rate_limiter(mock_redis):
    """Test OpenAI rate limiter."""
    limiter = OpenAIRateLimiter()
    limiter.redis = mock_redis

    # Mock Redis pipeline execution for both RPM and TPM checks
    pipeline = mock_redis.pipeline.return_value.__aenter__.return_value
    pipeline.execute.return_value = [None, None, 3, None]  # Under limit

    # Test successful wait
    await limiter.wait_if_needed(tokens=100)

    # Verify Redis calls
    assert mock_redis.pipeline.called


@pytest.mark.asyncio
async def test_openai_rate_limiter_exceeded(mock_redis):
    """Test OpenAI rate limiter when limit exceeded."""
    limiter = OpenAIRateLimiter()
    limiter.redis = mock_redis
    limiter.rpm_limit = 5
    limiter.max_retries = 2

    # Mock Redis pipeline execution
    pipeline = mock_redis.pipeline.return_value.__aenter__.return_value
    pipeline.execute.return_value = [None, None, 6, None]  # Over limit

    # Test rate limit exceeded
    with pytest.raises(RateLimitError) as exc_info:
        await limiter.wait_if_needed(tokens=100)

    assert "OpenAI rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_rate_limiter_backoff(mock_redis):
    """Test OpenAI rate limiter backoff strategy."""
    limiter = OpenAIRateLimiter()
    limiter.redis = mock_redis
    limiter.rpm_limit = 5
    limiter.backoff_factor = 1.5
    limiter.max_retries = 3

    # Mock Redis pipeline execution
    pipeline = mock_redis.pipeline.return_value.__aenter__.return_value
    # First two calls return over limit, third under limit
    pipeline.execute.side_effect = [
        [None, None, 6, None],  # First try
        [None, None, 6, None],  # Second try
        [None, None, 3, None],  # Third try
    ]

    with patch("asyncio.sleep") as mock_sleep:
        await limiter.wait_if_needed(tokens=100)

    # Verify backoff delays
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0][0][0] == 1.5  # First backoff
    assert mock_sleep.call_args_list[1][0][0] == 2.25  # Second backoff


@pytest.mark.asyncio
async def test_rate_limit_exempt():
    """Test rate limit exemption."""
    app = FastAPI()

    def is_admin(request: Request):
        return getattr(request.state, "is_admin", False)

    @app.get("/test")
    @rate_limit(limit=5, window=60, exempt_when=is_admin)
    async def test_endpoint(request: Request):
        return {"message": "success"}

    with patch("app.core.rate_limit.rate_limiter") as mock_limiter:
        # Create test client
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test admin request (should bypass rate limit)
        def admin_middleware(request: Request):
            request.state.is_admin = True
            return request

        app.middleware("http")(admin_middleware)
        response = client.get("/test")
        assert response.status_code == 200
        assert not mock_limiter.is_rate_limited.called


@pytest.mark.asyncio
async def test_rate_limit_headers():
    """Test rate limit headers in response."""
    app = FastAPI()

    @app.get("/test")
    @rate_limit(limit=5, window=60)
    async def test_endpoint(request: Request):
        return JSONResponse(
            content={"message": "success"},
            headers={"Custom-Header": "value"}
        )

    with patch("app.core.rate_limit.rate_limiter") as mock_limiter:
        # Mock rate limiter response
        mock_limiter.is_rate_limited.return_value = (False, {
            "limit": 5,
            "remaining": 4,
            "reset": datetime.now(timezone.utc).isoformat(),
            "window": 60
        })

        # Create test client
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test response headers
        response = client.get("/test")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["Custom-Header"] == "value"
