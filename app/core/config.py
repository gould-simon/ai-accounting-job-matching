"""Application configuration module."""
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.
    
    All settings are loaded from environment variables.
    """

    # Project paths
    PROJECT_ROOT: str = str(Path(__file__).parent.parent.parent)
    
    # Application
    VERSION: str = "1.0.0"
    
    # Environment
    BOT_ENV: str = "development"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    SQL_DEBUG: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30 minutes

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "text-embedding-ada-002"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT: int = 30
    OPENAI_RATE_LIMIT_RPM: int = 60  # Requests per minute
    OPENAI_RATE_LIMIT_TPM: int = 90000  # Tokens per minute

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: list[int] = []
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_MAX_CONNECTIONS: int = 40
    ADMIN_IDS: str
    TELEGRAM_ALLOWED_UPDATES: List[str] = ["message", "callback_query"]

    # Vector Search
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7
    MAX_SEARCH_RESULTS: int = 50

    # Service settings
    HEALTH_CHECK_INTERVAL: int = 60  # seconds
    MIN_SIMILARITY_SCORE: float = 0.7
    MAX_JOBS_PER_SEARCH: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    REDIS_TIMEOUT: int = 30

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_LIMIT: int = 60  # Requests per minute
    RATE_LIMIT_DEFAULT_WINDOW: int = 60  # Window in seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = ENVIRONMENT == "production"
    LOG_FILE: Optional[str] = None
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_FILTER_FIELDS: list[str] = [
        "password",
        "api_key",
        "token",
        "secret",
        "authorization",
    ]

    # Prometheus metrics
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Security
    CORS_ORIGINS: List[str] = ["*"]
    API_KEY_HEADER: str = "X-API-Key"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    CACHE_DIR: Path = BASE_DIR / "cache"
    LOG_DIR: Path = BASE_DIR / "logs"

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_log_file(self) -> Optional[str]:
        """Get log file path if logging to file is enabled.
        
        Returns:
            Log file path or None
        """
        if not self.LOG_FILE:
            return None
            
        # Ensure log directory exists
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        return str(self.LOG_DIR / self.LOG_FILE)

    @property
    def is_production(self) -> bool:
        """Check if running in production.
        
        Returns:
            True if in production
        """
        return self.BOT_ENV.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment.
        
        Returns:
            True if in test environment
        """
        return self.BOT_ENV.lower() == "test"

    def get_db_pool_settings(self) -> Dict[str, int]:
        """Get database connection pool settings.
        
        Returns:
            Dictionary of pool settings
        """
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
