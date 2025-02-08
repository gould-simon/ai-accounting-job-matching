"""Tests for API routes."""
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import DatabaseError, OpenAIError
from app.database import get_db
from app.main import create_app
from app.models.job import Job
from app.models.user import User
from app.schemas.api import JobResponse, UserPreferences


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application.
    
    Returns:
        FastAPI application
    """
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client.
    
    Args:
        app: FastAPI application
        
    Returns:
        Test client
    """
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client.
    
    Args:
        app: FastAPI application
        
    Yields:
        Async test client
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_job():
    """Create mock job."""
    return Job(
        id=1,
        title="Senior Accountant",
        company="Test Corp",
        location="London",
        description="Test job description",
        requirements="Test requirements",
        salary_range="£50,000 - £60,000",
        job_type="Full-time",
        experience_level="Senior",
        posted_date=datetime.now(timezone.utc),
        url="https://example.com/job/1"
    )


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(
        id=1,
        telegram_id=123456789,
        cv_text="Test CV",
        cv_updated_at=datetime.now(timezone.utc),
        preferences={
            "desired_roles": ["Accountant"],
            "locations": ["London"],
            "job_types": ["Full-time"],
            "remote_only": False,
            "notifications_enabled": True
        },
        total_searches=5,
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health check endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "timestamp" in data
    assert "database" in data
    assert "openai" in data


@pytest.mark.asyncio
async def test_search_jobs(async_client: AsyncClient, mock_db, mock_job):
    """Test job search endpoint."""
    # Mock embedding service
    with patch("app.services.embeddings.embedding_service.create_embedding") as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        # Mock job matching service
        with patch("app.services.job_matching.job_matching_service.search_jobs") as mock_search:
            mock_search.return_value = (1, [(mock_job, 0.95)])

            response = await async_client.post(
                "/api/v1/search",
                json={
                    "query": "senior accountant",
                    "location": "London",
                    "job_type": "Full-time",
                    "limit": 10
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "Senior Accountant"
            assert data["results"][0]["match_score"] == 0.95


@pytest.mark.asyncio
async def test_search_jobs_openai_error(async_client: AsyncClient):
    """Test job search with OpenAI error."""
    with patch("app.services.embeddings.embedding_service.create_embedding") as mock_embed:
        mock_embed.side_effect = OpenAIError(
            message="API error",
            error_code="OPENAI_ERROR"
        )

        response = await async_client.post(
            "/api/v1/search",
            json={"query": "accountant"}
        )

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "Failed to process search query"
        assert data["error_code"] == "OPENAI_ERROR"


@pytest.mark.asyncio
async def test_get_job(async_client: AsyncClient, mock_db, mock_job):
    """Test get job endpoint."""
    with patch("app.services.job_matching.job_matching_service.get_job") as mock_get:
        mock_get.return_value = mock_job

        response = await async_client.get("/api/v1/jobs/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Senior Accountant"


@pytest.mark.asyncio
async def test_get_job_not_found(async_client: AsyncClient, mock_db):
    """Test get job with non-existent ID."""
    with patch("app.services.job_matching.job_matching_service.get_job") as mock_get:
        mock_get.return_value = None

        response = await async_client.get("/api/v1/jobs/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_upload_cv(async_client: AsyncClient, mock_db):
    """Test CV upload endpoint."""
    # Create test file content
    file_content = b"Test CV content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    # Mock CV service
    with patch("app.services.cv.cv_service.extract_text") as mock_extract:
        mock_extract.return_value = "Test CV content"

        with patch("app.services.cv.cv_service.analyze_cv") as mock_analyze:
            mock_analyze.return_value = MagicMock(
                num_tokens=100,
                skills=["Python", "Accounting"],
                experience_years=5,
                suggested_roles=["Senior Accountant"]
            )

            with patch("app.services.cv.cv_service.store_cv") as mock_store:
                mock_store.return_value = 1

                response = await async_client.post(
                    "/api/v1/cv/upload",
                    files=files,
                    params={"user_id": 1}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["cv_id"] == 1
                assert data["text_extracted"] is True
                assert data["num_tokens"] == 100
                assert "Python" in data["skills"]
                assert data["experience_years"] == 5
                assert "Senior Accountant" in data["suggested_roles"]


@pytest.mark.asyncio
async def test_get_user_profile(async_client: AsyncClient, mock_db, mock_user):
    """Test get user profile endpoint."""
    with patch("app.services.user.user_service.get_user") as mock_get:
        mock_get.return_value = mock_user

        response = await async_client.get("/api/v1/users/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["telegram_id"] == 123456789
        assert data["cv_uploaded"] is True
        assert data["preferences"]["desired_roles"] == ["Accountant"]


@pytest.mark.asyncio
async def test_update_preferences(async_client: AsyncClient, mock_db):
    """Test update preferences endpoint."""
    preferences = {
        "desired_roles": ["Senior Accountant"],
        "locations": ["London", "Manchester"],
        "job_types": ["Full-time", "Contract"],
        "remote_only": True,
        "notifications_enabled": True
    }

    with patch("app.services.user.user_service.update_preferences") as mock_update:
        mock_update.return_value = True

        response = await async_client.put(
            "/api/v1/users/1/preferences",
            json=preferences
        )

        assert response.status_code == 200
        data = response.json()
        assert data == preferences


@pytest.mark.asyncio
async def test_rate_limiting(async_client: AsyncClient):
    """Test rate limiting middleware."""
    # Make multiple requests quickly
    responses = []
    for _ in range(70):  # Default limit is 60/minute
        response = await async_client.get("/api/v1/health")
        responses.append(response)

    # Check that some requests were rate limited
    assert any(r.status_code == 429 for r in responses)

    # Check rate limit headers
    success_response = next(r for r in responses if r.status_code == 200)
    assert "X-RateLimit-Limit" in success_response.headers
    assert "X-RateLimit-Remaining" in success_response.headers
    assert "X-RateLimit-Reset" in success_response.headers


@pytest.mark.asyncio
async def test_request_id_middleware(async_client: AsyncClient):
    """Test request ID middleware."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID length


@pytest.mark.asyncio
async def test_error_handling(async_client: AsyncClient):
    """Test error handling middleware."""
    with patch("app.services.job_matching.job_matching_service.get_job") as mock_get:
        mock_get.side_effect = DatabaseError(
            message="Database connection failed",
            error_code="DB_ERROR"
        )

        response = await async_client.get("/api/v1/jobs/1")

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "Database error occurred"
        assert data["error_code"] == "DB_ERROR"
        assert "request_id" in data
