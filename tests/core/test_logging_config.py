"""Tests for the logging configuration module."""

import json
import os
from pathlib import Path

import structlog

from app.core.logging_config import get_logger, setup_logging


def test_logging_setup(tmp_path: Path) -> None:
    """Test that logging is set up correctly."""
    # Set up logging with a temporary directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        setup_logging(log_level="DEBUG")

        # Check that the logs directory was created
        log_dir = Path("logs")
        assert log_dir.exists()
        assert log_dir.is_dir()

        # Get a logger and write some test messages
        logger = get_logger("test")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Check that the log file was created and contains valid JSON
        log_files = list(log_dir.glob("app_*.log"))
        assert len(log_files) == 1
        log_file = log_files[0]

        with open(log_file, "r") as f:
            for line in f:
                # Each line should be valid JSON
                log_entry = json.loads(line)
                assert "timestamp" in log_entry
    finally:
        os.chdir(original_cwd)


def test_logger_with_context() -> None:
    """Test that logger correctly handles structured context."""
    logger = get_logger("test_context")
    bound_logger = logger.bind(
        user_id="test_user",
        request_id="test_request",
    )

    # Capture log output
    with structlog.testing.capture_logs() as captured:
        bound_logger.info(
            "User action",
            action="test_action",
            status="success",
        )

        assert len(captured) == 1
        assert captured[0]["user_id"] == "test_user"
        assert captured[0]["request_id"] == "test_request"
        assert captured[0]["action"] == "test_action"
        assert captured[0]["status"] == "success"
        assert captured[0]["event"] == "User action"
