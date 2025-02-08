"""Tests for CV processing tasks."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.models.cv import CV
from app.tasks.cv import process_cv, cleanup_old_cvs


@pytest.mark.asyncio
async def test_process_cv_success(db_session, mock_cv_service, mock_openai_service):
    """Test successful CV processing."""
    # Setup
    cv = CV(
        id=1,
        user_id=1,
        file_path="/tmp/test.pdf",
        status="pending"
    )
    db_session.add(cv)
    await db_session.commit()
    
    mock_cv_service.extract_text.return_value = "Test CV content"
    mock_openai_service.analyze_cv.return_value = {
        "skills": ["Python", "SQL"],
        "experience": "5 years",
        "education": "Bachelor's"
    }
    mock_openai_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
    
    # Execute
    result = await process_cv(cv.id, cv.file_path, cv.user_id)
    
    # Verify
    assert result["success"] is True
    assert result["cv_id"] == cv.id
    
    # Check CV was updated
    cv = await db_session.get(CV, cv.id)
    assert cv.status == "processed"
    assert cv.extracted_text == "Test CV content"
    assert cv.analysis["skills"] == ["Python", "SQL"]
    assert cv.embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_process_cv_not_found(db_session):
    """Test CV processing when CV doesn't exist."""
    # Execute & Verify
    with pytest.raises(Exception) as exc:
        await process_cv(999, "/tmp/test.pdf", 1)
    assert "CV 999 not found" in str(exc.value)


@pytest.mark.asyncio
async def test_process_cv_extraction_failed(
    db_session,
    mock_cv_service
):
    """Test CV processing when text extraction fails."""
    # Setup
    cv = CV(
        id=1,
        user_id=1,
        file_path="/tmp/test.pdf",
        status="pending"
    )
    db_session.add(cv)
    await db_session.commit()
    
    mock_cv_service.extract_text.return_value = None
    
    # Execute & Verify
    with pytest.raises(Exception) as exc:
        await process_cv(cv.id, cv.file_path, cv.user_id)
    assert "Failed to extract text" in str(exc.value)


@pytest.mark.asyncio
async def test_cleanup_old_cvs(db_session, mock_cv_service):
    """Test cleanup of old CVs."""
    # Setup
    old_date = datetime.utcnow() - timedelta(days=31)
    new_date = datetime.utcnow() - timedelta(days=29)
    
    cvs = [
        CV(
            user_id=1,
            file_path="/tmp/old1.pdf",
            created_at=old_date,
            status="processed"
        ),
        CV(
            user_id=2,
            file_path="/tmp/old2.pdf",
            created_at=old_date,
            status="processed"
        ),
        CV(
            user_id=3,
            file_path="/tmp/new.pdf",
            created_at=new_date,
            status="processed"
        )
    ]
    
    for cv in cvs:
        db_session.add(cv)
    await db_session.commit()
    
    # Execute
    result = await cleanup_old_cvs(30)  # 30 days
    
    # Verify
    assert result["success"] is True
    assert result["deleted_count"] == 2
    
    # Check old CVs were deleted
    remaining_cvs = await db_session.query(CV).all()
    assert len(remaining_cvs) == 1
    assert remaining_cvs[0].file_path == "/tmp/new.pdf"
    
    # Check files were deleted
    assert mock_cv_service.delete_file.call_count == 2
    mock_cv_service.delete_file.assert_any_call("/tmp/old1.pdf")
    mock_cv_service.delete_file.assert_any_call("/tmp/old2.pdf")
