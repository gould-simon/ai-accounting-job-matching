"""Tests for embedding service."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from openai.types import CreateEmbeddingResponse
from openai.types.create_embedding_response import Embedding

from app.services.embeddings import EmbeddingService


@pytest.fixture
def mock_openai():
    """Create mock OpenAI client."""
    mock = MagicMock()
    mock.embeddings.create = AsyncMock(
        return_value=MagicMock(
            data=[
                MagicMock(
                    embedding=[0.1 for _ in range(1536)]
                )
            ]
        )
    )
    return mock


@pytest.fixture
def embedding_service(mock_openai):
    """Create embedding service with mock OpenAI client."""
    return EmbeddingService(mock_openai)


@pytest.mark.asyncio
async def test_create_embedding(embedding_service, mock_openai):
    """Test creating embedding vector."""
    # Test creating embedding
    embedding = await embedding_service.create_embedding("test text")
    
    # Verify embedding is returned
    assert isinstance(embedding, list)
    assert len(embedding) == 1536
    
    # Verify OpenAI was called correctly
    mock_openai.embeddings.create.assert_awaited_once_with(
        model="text-embedding-ada-002",
        input="test text",
    )


def test_calculate_similarity(embedding_service):
    """Test calculating embedding similarity."""
    # Test identical embeddings
    embedding1 = [1.0, 0.0, 0.0]
    embedding2 = [1.0, 0.0, 0.0]
    similarity = embedding_service.calculate_similarity(embedding1, embedding2)
    assert similarity == pytest.approx(1.0)
    
    # Test orthogonal embeddings
    embedding1 = [1.0, 0.0, 0.0]
    embedding2 = [0.0, 1.0, 0.0]
    similarity = embedding_service.calculate_similarity(embedding1, embedding2)
    assert similarity == pytest.approx(0.0)
    
    # Test opposite embeddings
    embedding1 = [1.0, 0.0, 0.0]
    embedding2 = [-1.0, 0.0, 0.0]
    similarity = embedding_service.calculate_similarity(embedding1, embedding2)
    assert similarity == pytest.approx(-1.0)


def test_combine_embeddings(embedding_service):
    """Test combining multiple embeddings."""
    # Test basic combination
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    combined = embedding_service.combine_embeddings(embeddings)
    assert len(combined) == 3
    assert combined[0] == pytest.approx(0.707107, rel=1e-5)
    assert combined[1] == pytest.approx(0.707107, rel=1e-5)
    assert combined[2] == pytest.approx(0.0)
    
    # Test weighted combination
    weights = [0.8, 0.2]
    combined = embedding_service.combine_embeddings(embeddings, weights)
    assert len(combined) == 3
    assert combined[0] > combined[1]  # First embedding should have more influence
    
    # Test empty input
    with pytest.raises(ValueError):
        embedding_service.combine_embeddings([])
    
    # Test mismatched weights
    with pytest.raises(ValueError):
        embedding_service.combine_embeddings(embeddings, [0.5])
