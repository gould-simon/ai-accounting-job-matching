"""Service for processing CV documents."""
import io
import logging
from typing import Optional

import docx
import pdfplumber

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CVProcessingService:
    """Service for processing CV documents."""

    async def extract_text(self, file_bytes: bytearray, filename: str) -> str:
        """Extract text from CV document.
        
        Args:
            file_bytes: Raw file bytes
            filename: Original filename
            
        Returns:
            Extracted text
            
        Raises:
            ValidationError: If file format is unsupported or processing fails
        """
        file_ext = filename.lower().split(".")[-1]
        
        try:
            if file_ext == "pdf":
                return await self._extract_from_pdf(file_bytes)
            elif file_ext in ["doc", "docx"]:
                return await self._extract_from_docx(file_bytes)
            else:
                raise ValidationError(
                    "Unsupported file format. Please upload a PDF or DOC file."
                )
                
        except Exception as e:
            logger.error(
                "Error extracting text from CV",
                extra={
                    "filename": filename,
                    "error": str(e)
                }
            )
            raise ValidationError(
                "Failed to process CV. Please make sure it's a valid file."
            )

    async def _extract_from_pdf(self, file_bytes: bytearray) -> str:
        """Extract text from PDF file.
        
        Args:
            file_bytes: Raw file bytes
            
        Returns:
            Extracted text
        """
        text = []
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
                
        return "\n".join(text)

    async def _extract_from_docx(self, file_bytes: bytearray) -> str:
        """Extract text from DOCX file.
        
        Args:
            file_bytes: Raw file bytes
            
        Returns:
            Extracted text
        """
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)


# Create service instance
cv_processing_service = CVProcessingService()
