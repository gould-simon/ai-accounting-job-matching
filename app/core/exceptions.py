"""
Exception handling framework for the AI Accounting Job Matching project.

This module defines custom exceptions and error handling utilities to ensure:
1. Consistent error reporting across the application
2. Proper logging of errors with context
3. User-friendly error messages
4. Safe handling of sensitive information
"""
from typing import Any, Dict, Optional
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseError(Exception):
    """Base exception class."""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        user_message: str = None,
        context: Dict[str, Any] = None,
        original_error: Exception = None,
    ) -> None:
        """Initialize exception.
        
        Args:
            message: Error message for logging
            error_code: Error code for categorizing errors
            user_message: User-friendly error message
            context: Additional context for logging
            original_error: Original exception if wrapping
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.user_message = user_message or message
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now(timezone.utc)

        # Add standard context
        self.context.update({
            "error_code": error_code,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.__class__.__name__
        })

        # Log the error
        logger.error(
            message,
            extra={
                "error_code": self.error_code,
                "error_type": self.__class__.__name__,
                "context": self.context,
                "original_error": str(self.original_error) if self.original_error else None
            },
            exc_info=self.original_error or True
        )


class JobMatchingError(BaseError):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the error with context and logging.
        
        Args:
            message: Technical error message for logging
            error_code: Unique error code for tracking
            user_message: User-friendly error message
            context: Additional context for debugging
            original_error: Original exception if this wraps another error
        """
        self.timestamp = datetime.now(timezone.utc)

        # Add standard context
        context = context or {}
        context.update({
            "error_code": error_code,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.__class__.__name__
        })

        # Log the error
        self._log_error(message)

        super().__init__(
            message=message,
            error_code=error_code,
            user_message=user_message or "An unexpected error occurred",
            context=context,
            original_error=original_error,
        )

    def _log_error(self, message: str) -> None:
        """Log the error with context."""
        logger.error(
            message,
            extra={
                "error_context": self.context,
                "original_error": str(self.original_error) if self.original_error else None
            }
        )


class DatabaseError(JobMatchingError):
    """Database-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize database error."""
        super().__init__(
            message=message,
            error_code="DB_ERROR",
            user_message="A database error occurred",
            context=self._sanitize_context(context),
            original_error=original_error
        )

    def _sanitize_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Remove sensitive information from context."""
        if not context:
            return {}
        
        # Create a copy to avoid modifying the original
        safe_context = context.copy()
        
        # Remove sensitive fields
        sensitive_fields = {"password", "token", "secret", "key"}
        for field in sensitive_fields:
            if field in safe_context:
                safe_context[field] = "[REDACTED]"
        
        return safe_context


class OpenAIError(JobMatchingError):
    """OpenAI API related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize OpenAI error."""
        super().__init__(
            message=message,
            error_code="OPENAI_ERROR",
            user_message="An error occurred while processing your request",
            context=context,
            original_error=original_error
        )


class ValidationError(JobMatchingError):
    """Data validation errors."""

    def __init__(
        self,
        message: str,
        field: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize validation error."""
        context = context or {}
        context["field"] = field
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            user_message=f"Invalid data provided for {field}",
            context=context,
            original_error=original_error
        )


class UserError(JobMatchingError):
    """User-related errors."""

    def __init__(
        self,
        message: str,
        telegram_id: int,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize user error."""
        context = context or {}
        context["telegram_id"] = telegram_id
        
        super().__init__(
            message=message,
            error_code="USER_ERROR",
            user_message="Unable to process user request",
            context=context,
            original_error=original_error
        )


class JobError(JobMatchingError):
    """Job-related errors."""

    def __init__(
        self,
        message: str,
        job_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize job error."""
        context = context or {}
        if job_id:
            context["job_id"] = job_id
        
        super().__init__(
            message=message,
            error_code="JOB_ERROR",
            user_message="Unable to process job data",
            context=context,
            original_error=original_error
        )


class TelegramError(JobMatchingError):
    """Telegram API related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize Telegram error."""
        super().__init__(
            message=message,
            error_code="TELEGRAM_ERROR",
            user_message="Unable to send message",
            context=context,
            original_error=original_error
        )


class RateLimitError(JobMatchingError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize rate limit error."""
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            user_message="Rate limit exceeded. Please try again later.",
            context=context,
            original_error=original_error
        )


class CVProcessingError(JobMatchingError):
    """CV processing related errors."""

    def __init__(
        self,
        message: str,
        cv_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize CV processing error."""
        context = context or {}
        if cv_id:
            context["cv_id"] = cv_id
        
        super().__init__(
            message=message,
            error_code="CV_PROCESSING_ERROR",
            user_message="Unable to process CV data",
            context=context,
            original_error=original_error
        )


class ServiceError(JobMatchingError):
    """Service-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize service error."""
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            user_message="An error occurred in the service",
            context=context,
            original_error=original_error
        )


class BotError(BaseError):
    """Bot-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        user_message: str = None,
        context: Dict[str, Any] = None,
        original_error: Exception = None,
    ) -> None:
        """Initialize bot error."""
        super().__init__(
            message=message,
            error_code=error_code or "BOT_ERROR",
            user_message=user_message or "An error occurred in the bot",
            context=context,
            original_error=original_error,
        )


def handle_error(error: Exception) -> Dict[str, Any]:
    """Convert any error to a standardized response format.
    
    Args:
        error: The exception to handle

    Returns:
        Dict containing error details in a standard format
    """
    if isinstance(error, BaseError):
        return {
            "error": True,
            "error_code": error.error_code,
            "message": error.user_message,
            "details": error.context
        }
    
    # Wrap unknown errors
    wrapped_error = JobMatchingError(
        message=str(error),
        error_code="UNKNOWN_ERROR",
        user_message="An unexpected error occurred",
        original_error=error
    )
    
    return {
        "error": True,
        "error_code": wrapped_error.error_code,
        "message": wrapped_error.user_message,
        "details": wrapped_error.context
    }


def safe_execute(func: callable, error_message: str, **kwargs) -> Any:
    """Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        error_message: Message to use if an error occurs
        **kwargs: Additional context to include in error

    Returns:
        The function's return value

    Raises:
        JobMatchingError: If an error occurs during execution
    """
    try:
        return func()
    except Exception as e:
        if isinstance(e, JobMatchingError):
            raise
        
        raise JobMatchingError(
            message=error_message,
            error_code="EXECUTION_ERROR",
            context=kwargs,
            original_error=e
        ) from e
