"""Tests for CV processor service."""
import json
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CVProcessingError, OpenAIError
from app.models.cv import CV
from app.models.user import User
from app.services.cv_processor import CVProcessor


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = AsyncMock()
    
    # Mock chat completion
    chat_completion = AsyncMock()
    chat_completion.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "personal_details": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+1234567890",
                        "location": "London"
                    },
                    "skills": [
                        "Python",
                        "SQL",
                        "Data Analysis"
                    ],
                    "experiences": [
                        {
                            "company": "Tech Corp",
                            "title": "Senior Developer",
                            "location": "London",
                            "start_date": "2020-01-01",
                            "end_date": "2023-01-01",
                            "is_current": False,
                            "description": "Led development team",
                            "skills": ["Python", "SQL"]
                        }
                    ],
                    "education": [
                        {
                            "institution": "University of London",
                            "degree": "BSc Computer Science",
                            "field_of_study": "Computer Science",
                            "start_date": "2016-09-01",
                            "end_date": "2020-06-01",
                            "grade": "First Class",
                            "activities": ["Programming Club"]
                        }
                    ]
                })
            )
        )
    ]
    client.chat.completions.create = AsyncMock(
        return_value=chat_completion
    )
    
    # Mock embedding
    embedding = AsyncMock()
    embedding.data = [
        MagicMock(embedding=[0.1] * 1536)
    ]
    client.embeddings.create = AsyncMock(
        return_value=embedding
    )
    
    return client


@pytest.fixture
def sample_cv_text():
    """Sample CV text for testing."""
    return """
    John Doe
    Email: john@example.com
    Phone: +1234567890
    Location: London

    Skills:
    - Python
    - SQL
    - Data Analysis

    Experience:
    Tech Corp (2020-2023)
    Senior Developer
    - Led development team
    - Used Python and SQL

    Education:
    University of London (2016-2020)
    BSc Computer Science
    First Class Honours
    """


@pytest.fixture
async def cv_processor(
    db_session: AsyncSession,
    mock_openai_client
) -> CVProcessor:
    """Create CV processor."""
    return CVProcessor(
        session=db_session,
        openai_client=mock_openai_client
    )


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample user."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_process_pdf_cv(
    cv_processor: CVProcessor,
    sample_user: User,
    tmp_path: Path
):
    """Test processing PDF CV."""
    # Create a sample PDF file
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF")  # Minimal PDF content

    with patch("pdfplumber.open") as mock_pdf:
        # Mock PDF text extraction
        mock_pdf.return_value.__enter__.return_value.pages = [
            MagicMock(extract_text=lambda: "Sample CV text")
        ]

        cv = await cv_processor.process_cv(
            user_id=sample_user.id,
            file_path=str(pdf_path),
            original_filename="test.pdf",
            content_type="application/pdf",
            file_size=1024
        )

        assert cv is not None
        assert cv.user_id == sample_user.id
        assert cv.original_filename == "test.pdf"
        assert cv.content_type == "application/pdf"
        assert cv.file_size == 1024
        assert cv.raw_text is not None
        assert cv.structured_data is not None
        assert cv.embedding is not None
        assert cv.skills is not None
        assert len(cv.extracted_experiences) == 1
        assert len(cv.extracted_educations) == 1


@pytest.mark.asyncio
async def test_process_docx_cv(
    cv_processor: CVProcessor,
    sample_user: User,
    tmp_path: Path
):
    """Test processing DOCX CV."""
    # Create a sample DOCX file
    docx_path = tmp_path / "test.docx"
    docx_path.write_bytes(b"PK\x03\x04")  # Minimal DOCX content

    with patch("docx.Document") as mock_docx:
        # Mock DOCX text extraction
        mock_docx.return_value.paragraphs = [
            MagicMock(text="Sample CV text")
        ]

        cv = await cv_processor.process_cv(
            user_id=sample_user.id,
            file_path=str(docx_path),
            original_filename="test.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=1024
        )

        assert cv is not None
        assert cv.user_id == sample_user.id
        assert cv.original_filename == "test.docx"
        assert cv.structured_data is not None
        assert cv.embedding is not None


@pytest.mark.asyncio
async def test_unsupported_file_type(
    cv_processor: CVProcessor,
    sample_user: User,
    tmp_path: Path
):
    """Test processing unsupported file type."""
    # Create a sample text file
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("Sample CV")

    with pytest.raises(CVProcessingError) as exc_info:
        await cv_processor.process_cv(
            user_id=sample_user.id,
            file_path=str(txt_path),
            original_filename="test.txt",
            content_type="text/plain",
            file_size=1024
        )
    
    assert "Unsupported file type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_analysis_error(
    cv_processor: CVProcessor,
    sample_user: User,
    tmp_path: Path
):
    """Test OpenAI analysis error handling."""
    # Create a sample PDF file
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF")

    # Make OpenAI analysis fail
    cv_processor.openai_client.chat.completions.create.side_effect = Exception(
        "OpenAI API error"
    )

    with pytest.raises(OpenAIError) as exc_info:
        with patch("pdfplumber.open") as mock_pdf:
            mock_pdf.return_value.__enter__.return_value.pages = [
                MagicMock(extract_text=lambda: "Sample CV text")
            ]
            
            await cv_processor.process_cv(
                user_id=sample_user.id,
                file_path=str(pdf_path),
                original_filename="test.pdf",
                content_type="application/pdf",
                file_size=1024
            )
    
    assert "Failed to analyze CV with OpenAI" in str(exc_info.value)


@pytest.mark.asyncio
async def test_embedding_error(
    cv_processor: CVProcessor,
    sample_user: User,
    tmp_path: Path
):
    """Test embedding generation error handling."""
    # Create a sample PDF file
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF")

    # Make embedding generation fail
    cv_processor.openai_client.embeddings.create.side_effect = Exception(
        "OpenAI API error"
    )

    with pytest.raises(OpenAIError) as exc_info:
        with patch("pdfplumber.open") as mock_pdf:
            mock_pdf.return_value.__enter__.return_value.pages = [
                MagicMock(extract_text=lambda: "Sample CV text")
            ]
            
            await cv_processor.process_cv(
                user_id=sample_user.id,
                file_path=str(pdf_path),
                original_filename="test.pdf",
                content_type="application/pdf",
                file_size=1024
            )
    
    assert "Failed to generate CV embedding" in str(exc_info.value)
