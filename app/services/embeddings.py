"""Embedding service for generating and managing embeddings."""

import logging
from typing import List, Optional

import openai
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import OpenAIError, ValidationError
from app.core.logging import get_logger
from app.core.rate_limit import openai_rate_limiter
from app.services.base import BaseService

logger = get_logger(__name__)


class EmbeddingService(BaseService):
    """Service for creating and managing text embeddings."""

    def __init__(self) -> None:
        """Initialize embedding service."""
        super().__init__()
        self.model = settings.OPENAI_MODEL
        self.encoding = tiktoken.encoding_for_model(self.model)
        self.max_text_length = 8191  # OpenAI's max token limit

    async def init(self) -> None:
        """Initialize the embedding service."""
        # Initialize OpenAI rate limiter
        await openai_rate_limiter.init()
        await self._init_resources()
        logger.info("Embedding service initialized")

    async def close(self) -> None:
        """Close the embedding service."""
        # Close OpenAI rate limiter
        await openai_rate_limiter.close()
        await self._cleanup_resources()
        logger.info("Embedding service closed")

    async def _init_resources(self) -> None:
        """Initialize OpenAI client."""
        openai.api_key = settings.OPENAI_API_KEY
        # Test OpenAI connection
        try:
            await self.generate_embedding("test")
            logger.info("OpenAI connection verified")
        except Exception as e:
            logger.error("Failed to connect to OpenAI", exc_info=e)
            raise

    async def _cleanup_resources(self) -> None:
        """No cleanup needed for OpenAI client."""
        pass

    async def _check_health(self) -> bool:
        """Check OpenAI connection."""
        try:
            await self.generate_embedding("health check")
            return True
        except Exception as e:
            logger.error("OpenAI health check failed", exc_info=e)
            return False

    def _validate_text(self, text: str) -> str:
        """Validate and clean text for embedding.

        Args:
            text: Text to validate

        Returns:
            Cleaned text

        Raises:
            ValidationError: If text is invalid
        """
        if not text or not isinstance(text, str):
            raise ValidationError("Text must be a non-empty string")

        # Clean text
        text = text.replace("\n", " ").strip()

        # Check length
        tokens = len(self.encoding.encode(text))
        if tokens > self.max_text_length:
            raise ValidationError(
                f"Text is too long ({tokens} tokens). Maximum is {self.max_text_length} tokens."
            )

        return text

    @openai_rate_limiter
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI.

        Args:
            text: Text to generate embedding for

        Returns:
            List of embedding values

        Raises:
            ValidationError: If text is invalid
            OpenAIError: If embedding generation fails
        """
        try:
            # Validate and clean text
            text = self._validate_text(text)

            # Get embedding from OpenAI
            response = await openai.Embedding.acreate(input=text, model=self.model)

            # Extract embedding values
            embedding = response["data"][0]["embedding"]

            logger.debug(
                "Generated embedding",
                extra={"text_length": len(text), "embedding_length": len(embedding)},
            )

            return embedding

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to generate embedding",
                exc_info=e,
                extra={"text_length": len(text)},
            )
            raise OpenAIError("Failed to generate embedding") from e


# Global embedding service instance
embedding_service = EmbeddingService()
