"""Logging configuration and utilities for the AI Accounting Job Matching project."""
import json
import logging
import logging.config
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pythonjsonlogger import jsonlogger

from app.core.config import settings

# Create logs directory if it doesn't exist
LOG_DIR = Path(settings.PROJECT_ROOT) / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Define log files
BOT_LOG = LOG_DIR / "bot.log"
API_LOG = LOG_DIR / "api.log"
ERROR_LOG = LOG_DIR / "error.log"

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive information from logs."""

    SENSITIVE_FIELDS = {
        "password",
        "api_key",
        "token",
        "secret",
        "authorization",
        "access_token",
        "refresh_token",
        "private_key",
        "cv_text",  # User CV content
        "embedding",  # Raw embedding values
    }

    def __init__(self) -> None:
        """Initialize filter."""
        super().__init__()
        self.replace_with = "[REDACTED]"

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log record."""
        if isinstance(record.args, dict):
            record.args = self._filter_dict(record.args)
        elif isinstance(record.args, (list, tuple)):
            record.args = tuple(
                self._filter_dict(arg) if isinstance(arg, dict) else arg
                for arg in record.args
            )

        # Filter extra fields
        if hasattr(record, "extra"):
            record.extra = self._filter_dict(record.extra)

        return True

    def _filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter dictionary values."""
        if not isinstance(data, dict):
            return data

        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                filtered[key] = self.replace_with
            elif isinstance(value, dict):
                filtered[key] = self._filter_dict(value)
            elif isinstance(value, (list, tuple)):
                filtered[key] = [
                    self._filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record.update(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "logger": record.name,
                "level": record.levelname,
                "environment": settings.ENVIRONMENT,
                "version": settings.VERSION,
            }
        )

        # Add error details if present
        if record.exc_info:
            log_record["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Set up logging configuration."""
    # Create formatter
    if json_logs:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handlers
    handlers = {
        "bot": BOT_LOG,
        "api": API_LOG,
        "error": ERROR_LOG,
    }

    for name, path in handlers.items():
        handler = logging.FileHandler(path)
        handler.setFormatter(formatter)
        
        if name == "error":
            handler.setLevel(logging.ERROR)
            
        logger = logging.getLogger(f"app.{name}")
        logger.addHandler(handler)

    # Add sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)

    # Log startup message
    logging.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "json_logs": json_logs,
            "log_files": {name: str(path) for name, path in handlers.items()},
        },
    )


@contextmanager
def log_context(**kwargs: Any):
    """Context manager to add context to logs."""
    thread = logging.getLogger()
    old_thread_extra = getattr(thread, "extra", {})
    thread.extra = {**old_thread_extra, **kwargs}
    try:
        yield
    finally:
        thread.extra = old_thread_extra


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
