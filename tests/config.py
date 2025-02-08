"""Test configuration module."""
import os
from typing import Dict, Any

# Test database configuration
TEST_DATABASE_CONFIG: Dict[str, Any] = {
    "TEST_DATABASE_URL": os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/jobmatch_test"),
    "ECHO_SQL": False,
    "POOL_SIZE": 5,
    "MAX_OVERFLOW": 10,
    "POOL_TIMEOUT": 30,
}

# Test OpenAI configuration
TEST_OPENAI_CONFIG: Dict[str, Any] = {
    "API_KEY": os.getenv("TEST_OPENAI_API_KEY", "test_key"),
    "MODEL": "text-embedding-ada-002",
    "EMBEDDING_DIMENSIONS": 1536,
}

# Test Telegram configuration
TEST_TELEGRAM_CONFIG: Dict[str, Any] = {
    "BOT_TOKEN": os.getenv("TEST_TELEGRAM_BOT_TOKEN", "test_token"),
    "WEBHOOK_URL": "https://test.example.com/webhook",
}

# Test logging configuration
TEST_LOGGING_CONFIG: Dict[str, Any] = {
    "LEVEL": "DEBUG",
    "FORMAT": "json",
    "FILTER_FIELDS": ["password", "api_key", "token"],
}

# Test rate limiting
TEST_RATE_LIMITS: Dict[str, Any] = {
    "OPENAI_RPM": 10,  # Requests per minute
    "TELEGRAM_RPM": 20,
    "JOB_SEARCH_RPM": 30,
}

# Test feature flags
TEST_FEATURES: Dict[str, bool] = {
    "ENABLE_CV_PARSING": True,
    "ENABLE_JOB_MATCHING": True,
    "ENABLE_RECOMMENDATIONS": True,
}

# Test timeouts (in seconds)
TEST_TIMEOUTS: Dict[str, int] = {
    "DATABASE": 5,
    "API_CALL": 3,
    "LONG_OPERATION": 10,
}

# Test paths
TEST_PATHS: Dict[str, str] = {
    "UPLOAD_DIR": "/tmp/test_uploads",
    "CACHE_DIR": "/tmp/test_cache",
    "LOG_DIR": "/tmp/test_logs",
}

# Combine all test configurations
TEST_CONFIG: Dict[str, Dict[str, Any]] = {
    "DATABASE": TEST_DATABASE_CONFIG,
    "OPENAI": TEST_OPENAI_CONFIG,
    "TELEGRAM": TEST_TELEGRAM_CONFIG,
    "LOGGING": TEST_LOGGING_CONFIG,
    "RATE_LIMITS": TEST_RATE_LIMITS,
    "FEATURES": TEST_FEATURES,
    "TIMEOUTS": TEST_TIMEOUTS,
    "PATHS": TEST_PATHS,
}
