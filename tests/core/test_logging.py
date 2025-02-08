"""Tests for logging configuration and utilities."""
import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.logging import (
    CustomJsonFormatter,
    RequestContext,
    SensitiveDataFilter,
    get_logger,
    log_context,
    setup_logging,
)


def test_sensitive_data_filter():
    """Test sensitive data filtering."""
    filter_ = SensitiveDataFilter()
    
    # Test dictionary filtering
    data = {
        "username": "test",
        "password": "secret",
        "api_key": "key123",
        "nested": {
            "token": "abc",
            "safe": "visible"
        },
        "list": [
            {"secret": "hidden"},
            {"visible": "shown"}
        ]
    }
    
    filtered = filter_._filter_dict(data)
    
    assert filtered["username"] == "test"
    assert filtered["password"] == "[REDACTED]"
    assert filtered["api_key"] == "[REDACTED]"
    assert filtered["nested"]["token"] == "[REDACTED]"
    assert filtered["nested"]["safe"] == "visible"
    assert filtered["list"][0]["secret"] == "[REDACTED]"
    assert filtered["list"][1]["visible"] == "shown"


def test_custom_json_formatter():
    """Test custom JSON formatter."""
    formatter = CustomJsonFormatter()
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Add request ID
    setattr(record, "request_id", "test-123")
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert "timestamp" in data
    assert data["level"] == "INFO"
    assert data["request_id"] == "test-123"
    assert "environment" in data


def test_request_context():
    """Test request context manager."""
    with RequestContext() as ctx:
        assert ctx.request_id is not None
        assert ctx.start_time is not None
        
        # Simulate some work
        with patch("logging.Logger.info") as mock_log:
            pass
    
    # Check completion log
    mock_log.assert_called_once()
    call_args = mock_log.call_args[1]
    assert "Request completed" in call_args.get("extra", {})
    assert "duration_seconds" in call_args.get("extra", {})


def test_log_context():
    """Test log context manager."""
    logger = logging.getLogger("test")
    
    with log_context(user_id=123, action="test"):
        with patch.object(logger, "info") as mock_log:
            logger.info("Test message")
    
    mock_log.assert_called_once()
    record = mock_log.call_args[0][0]
    assert hasattr(record, "user_id")
    assert hasattr(record, "action")
    assert record.user_id == 123
    assert record.action == "test"


def test_get_logger():
    """Test logger retrieval."""
    logger = get_logger("test")
    assert logger.name == "app.test"


def test_setup_logging_json(tmp_path):
    """Test logging setup with JSON format."""
    log_file = tmp_path / "test.log"
    
    setup_logging(
        log_level="DEBUG",
        json_logs=True,
        log_file=str(log_file)
    )
    
    logger = logging.getLogger("app.test")
    logger.info("Test message", extra={"test_key": "test_value"})
    
    # Check file contents
    with open(log_file) as f:
        log_entry = json.loads(f.readline())
        assert log_entry["message"] == "Test message"
        assert log_entry["test_key"] == "test_value"
        assert "timestamp" in log_entry
        assert log_entry["level"] == "INFO"


def test_setup_logging_standard(tmp_path):
    """Test logging setup with standard format."""
    log_file = tmp_path / "test.log"
    
    setup_logging(
        log_level="DEBUG",
        json_logs=False,
        log_file=str(log_file)
    )
    
    logger = logging.getLogger("app.test")
    logger.info("Test message")
    
    # Check file contents
    with open(log_file) as f:
        log_line = f.readline()
        assert "Test message" in log_line
        assert "[INFO]" in log_line


def test_sensitive_data_in_logs():
    """Test sensitive data filtering in actual logs."""
    logger = get_logger("test")
    
    with patch("logging.Logger.info") as mock_log:
        logger.info(
            "User login",
            extra={
                "username": "test",
                "password": "secret",
                "token": "abc123"
            }
        )
    
    mock_log.assert_called_once()
    extra = mock_log.call_args[1].get("extra", {})
    assert extra["username"] == "test"
    assert extra["password"] == "[REDACTED]"
    assert extra["token"] == "[REDACTED]"


def test_error_logging():
    """Test error logging with traceback."""
    logger = get_logger("test")
    
    try:
        raise ValueError("Test error")
    except ValueError:
        with patch("logging.Logger.error") as mock_log:
            logger.error("Error occurred", exc_info=True)
    
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert call_args[0][0] == "Error occurred"
    assert call_args[1]["exc_info"] is True


@pytest.mark.asyncio
async def test_async_context_logging():
    """Test logging in async context."""
    logger = get_logger("test")
    
    async with RequestContext() as ctx:
        with patch("logging.Logger.info") as mock_log:
            logger.info(
                "Async operation",
                extra={"request_id": ctx.request_id}
            )
    
    mock_log.assert_called()
    extra = mock_log.call_args[1].get("extra", {})
    assert "request_id" in extra


def test_logging_levels():
    """Test different logging levels."""
    logger = get_logger("test")
    
    with patch("logging.Logger.debug") as debug_mock:
        logger.debug("Debug message")
    debug_mock.assert_called_once()
    
    with patch("logging.Logger.info") as info_mock:
        logger.info("Info message")
    info_mock.assert_called_once()
    
    with patch("logging.Logger.warning") as warning_mock:
        logger.warning("Warning message")
    warning_mock.assert_called_once()
    
    with patch("logging.Logger.error") as error_mock:
        logger.error("Error message")
    error_mock.assert_called_once()


def test_nested_context():
    """Test nested logging contexts."""
    logger = get_logger("test")
    
    with log_context(outer="value1"):
        with log_context(inner="value2"):
            with patch("logging.Logger.info") as mock_log:
                logger.info("Nested context")
    
    mock_log.assert_called_once()
    record = mock_log.call_args[0][0]
    assert hasattr(record, "outer")
    assert hasattr(record, "inner")
    assert record.outer == "value1"
    assert record.inner == "value2"
