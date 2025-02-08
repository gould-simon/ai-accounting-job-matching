"""Tests for the error handling framework."""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.core.exceptions import (
    JobMatchingError,
    DatabaseError,
    OpenAIError,
    ValidationError,
    UserError,
    JobError,
    TelegramError,
    handle_error,
    safe_execute,
)


def test_base_error_initialization():
    """Test JobMatchingError initialization."""
    error = JobMatchingError(
        message="Test error",
        error_code="TEST_ERROR",
        user_message="User message",
        context={"test": "data"}
    )
    
    assert error.error_code == "TEST_ERROR"
    assert error.user_message == "User message"
    assert error.context["test"] == "data"
    assert "timestamp" in error.context
    assert "error_type" in error.context
    assert error.context["error_type"] == "JobMatchingError"


def test_database_error_sanitization():
    """Test DatabaseError removes sensitive information."""
    context = {
        "password": "secret",
        "api_key": "key123",
        "safe_field": "visible",
    }
    
    error = DatabaseError(
        message="Database error",
        context=context
    )
    
    assert error.context["password"] == "[REDACTED]"
    assert error.context["api_key"] == "[REDACTED]"
    assert error.context["safe_field"] == "visible"


def test_validation_error_with_field():
    """Test ValidationError includes field information."""
    error = ValidationError(
        message="Invalid email",
        field="email",
        context={"value": "invalid@email"}
    )
    
    assert error.context["field"] == "email"
    assert "Invalid data provided for email" in error.user_message


def test_user_error_with_telegram_id():
    """Test UserError includes telegram_id."""
    error = UserError(
        message="User not found",
        telegram_id=123456789
    )
    
    assert error.context["telegram_id"] == 123456789


def test_job_error_optional_job_id():
    """Test JobError handles optional job_id."""
    # Test with job_id
    error_with_id = JobError(
        message="Job not found",
        job_id=1
    )
    assert error_with_id.context["job_id"] == 1
    
    # Test without job_id
    error_without_id = JobError(
        message="General job error"
    )
    assert "job_id" not in error_without_id.context


def test_error_handler_known_error():
    """Test handle_error with JobMatchingError."""
    error = JobMatchingError(
        message="Known error",
        error_code="KNOWN_ERROR",
        user_message="User message"
    )
    
    result = handle_error(error)
    
    assert result["success"] is False
    assert result["error"]["code"] == "KNOWN_ERROR"
    assert result["error"]["message"] == "User message"
    assert "timestamp" in result["error"]


def test_error_handler_unknown_error():
    """Test handle_error with unknown error."""
    error = ValueError("Unknown error")
    
    result = handle_error(error)
    
    assert result["success"] is False
    assert result["error"]["code"] == "UNKNOWN_ERROR"
    assert result["error"]["message"] == "An unexpected error occurred"
    assert "timestamp" in result["error"]


def test_safe_execute_success():
    """Test safe_execute with successful execution."""
    def success_func():
        return "success"
    
    result = safe_execute(
        success_func,
        "Error message",
        context="test"
    )
    
    assert result == "success"


def test_safe_execute_failure():
    """Test safe_execute with failing function."""
    def failing_func():
        raise ValueError("Original error")
    
    with pytest.raises(JobMatchingError) as exc_info:
        safe_execute(
            failing_func,
            "Error message",
            context="test"
        )
    
    assert exc_info.value.error_code == "EXECUTION_ERROR"
    assert exc_info.value.context["context"] == "test"
    assert str(exc_info.value.original_error) == "Original error"


@pytest.mark.asyncio
async def test_async_error_handling():
    """Test error handling in async context."""
    async def async_failing_func():
        raise ValueError("Async error")
    
    with pytest.raises(JobMatchingError) as exc_info:
        await async_failing_func()
    
    error_response = handle_error(exc_info.value)
    assert error_response["success"] is False


def test_error_logging(caplog):
    """Test error logging functionality."""
    with caplog.at_level("ERROR"):
        error = JobMatchingError(
            message="Test log message",
            error_code="LOG_TEST",
            context={"test": "logging"}
        )
        
        assert "Test log message" in caplog.text
        assert "LOG_TEST" in str(caplog.records[0].error_context)


def test_telegram_error_handling():
    """Test TelegramError specific handling."""
    error = TelegramError(
        message="Failed to send message",
        context={"chat_id": 123456789}
    )
    
    assert error.error_code == "TELEGRAM_ERROR"
    assert "chat_id" in error.context


def test_openai_error_handling():
    """Test OpenAIError specific handling."""
    error = OpenAIError(
        message="API rate limit exceeded",
        context={"model": "text-embedding-ada-002"}
    )
    
    assert error.error_code == "OPENAI_ERROR"
    assert "model" in error.context


@pytest.mark.parametrize("error_class,expected_code", [
    (DatabaseError, "DB_ERROR"),
    (OpenAIError, "OPENAI_ERROR"),
    (ValidationError, "VALIDATION_ERROR"),
    (UserError, "USER_ERROR"),
    (JobError, "JOB_ERROR"),
    (TelegramError, "TELEGRAM_ERROR"),
])
def test_error_codes(error_class, expected_code):
    """Test error codes for different error types."""
    error = error_class(message="Test error")
    assert error.error_code == expected_code
