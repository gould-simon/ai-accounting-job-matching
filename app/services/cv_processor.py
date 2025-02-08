"""Service for processing and analyzing CVs."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
from docx import Document
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import CVProcessingError, OpenAIError
from app.models.cv import CV
from app.repositories.cv import CVRepository

logger = logging.getLogger(__name__)


class CVProcessor:
    """Service for processing and analyzing CVs."""

    def __init__(
        self,
        session: AsyncSession,
        openai_client: Optional[AsyncOpenAI] = None
    ) -> None:
        """Initialize CV processor.
        
        Args:
            session: Database session
            openai_client: Optional OpenAI client (for testing)
        """
        self.session = session
        self.cv_repo = CVRepository(session)
        self.openai_client = openai_client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    async def process_cv(
        self,
        user_id: int,
        file_path: str,
        original_filename: str,
        content_type: str,
        file_size: int
    ) -> CV:
        """Process a CV file.
        
        Args:
            user_id: User ID
            file_path: Path to uploaded file
            original_filename: Original filename
            content_type: File content type
            file_size: File size in bytes
            
        Returns:
            Processed CV record
            
        Raises:
            CVProcessingError: If CV processing fails
        """
        try:
            # Create CV record
            cv = await self.cv_repo.create_cv(
                user_id=user_id,
                original_filename=original_filename,
                file_path=file_path,
                content_type=content_type,
                file_size=file_size
            )

            # Extract text
            raw_text = await self._extract_text(file_path, content_type)

            # Analyze with OpenAI
            structured_data = await self._analyze_cv(raw_text)
            
            # Generate embedding
            embedding = await self._generate_embedding(raw_text)

            # Extract skills
            skills = structured_data.get("skills", [])

            # Update CV with extracted data
            cv = await self.cv_repo.update_extracted_data(
                cv_id=cv.id,
                raw_text=raw_text,
                structured_data=structured_data,
                embedding=embedding,
                skills=skills
            )

            # Add experiences
            for exp in structured_data.get("experiences", []):
                await self.cv_repo.add_experience(
                    cv_id=cv.id,
                    company=exp["company"],
                    title=exp["title"],
                    location=exp.get("location"),
                    start_date=self._parse_date(exp.get("start_date")),
                    end_date=self._parse_date(exp.get("end_date")),
                    is_current=exp.get("is_current", False),
                    description=exp.get("description"),
                    skills=exp.get("skills", [])
                )

            # Add education
            for edu in structured_data.get("education", []):
                await self.cv_repo.add_education(
                    cv_id=cv.id,
                    institution=edu["institution"],
                    degree=edu["degree"],
                    field_of_study=edu.get("field_of_study"),
                    location=edu.get("location"),
                    start_date=self._parse_date(edu.get("start_date")),
                    end_date=self._parse_date(edu.get("end_date")),
                    is_current=edu.get("is_current", False),
                    grade=edu.get("grade"),
                    activities=edu.get("activities", [])
                )

            return cv

        except Exception as e:
            raise CVProcessingError(
                message="Failed to process CV",
                context={
                    "user_id": user_id,
                    "original_filename": original_filename
                },
                original_error=e
            )

    async def _extract_text(self, file_path: str, content_type: str) -> str:
        """Extract text from CV file.
        
        Args:
            file_path: Path to file
            content_type: File content type
            
        Returns:
            Extracted text
            
        Raises:
            CVProcessingError: If text extraction fails
        """
        try:
            path = Path(file_path)
            
            if content_type == "application/pdf":
                with pdfplumber.open(path) as pdf:
                    return "\n".join(
                        page.extract_text() for page in pdf.pages
                    )
            
            elif content_type in [
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                doc = Document(path)
                return "\n".join(
                    paragraph.text for paragraph in doc.paragraphs
                )
            
            else:
                raise CVProcessingError(
                    message=f"Unsupported file type: {content_type}",
                    context={"content_type": content_type}
                )

        except Exception as e:
            raise CVProcessingError(
                message="Failed to extract text from CV",
                context={
                    "file_path": file_path,
                    "content_type": content_type
                },
                original_error=e
            )

    async def _analyze_cv(self, text: str) -> Dict:
        """Analyze CV text using OpenAI.
        
        Args:
            text: CV text content
            
        Returns:
            Structured CV data
            
        Raises:
            OpenAIError: If OpenAI analysis fails
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a CV analyzer. Extract the following information in JSON format:
                            - Personal details (name, email, phone, location)
                            - Skills (list of technical and soft skills)
                            - Work experiences (company, title, location, dates, description, skills used)
                            - Education (institution, degree, field, dates, grade, activities)
                            
                            Format dates as YYYY-MM-DD. Mark current positions with is_current=true."""
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            return response.choices[0].message.content

        except Exception as e:
            raise OpenAIError(
                message="Failed to analyze CV with OpenAI",
                original_error=e
            )

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for CV text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            OpenAIError: If embedding generation fails
        """
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text[:8191]  # OpenAI's token limit
            )
            return response.data[0].embedding

        except Exception as e:
            raise OpenAIError(
                message="Failed to generate CV embedding",
                original_error=e
            )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Parsed datetime or None
        """
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None
