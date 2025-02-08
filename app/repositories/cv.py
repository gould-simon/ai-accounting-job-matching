"""CV repository for database operations."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DatabaseError, UserError
from app.models.cv import CV, CVExperience, CVEducation
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CVRepository(BaseRepository[CV]):
    """Repository for CV-related database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with CV model."""
        super().__init__(CV, session)

    async def get_with_details(self, cv_id: int) -> Optional[CV]:
        """Get CV with all related details.
        
        Args:
            cv_id: CV ID
            
        Returns:
            CV with loaded relationships if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(CV)
                .options(
                    selectinload(CV.extracted_experiences),
                    selectinload(CV.extracted_educations)
                )
                .where(CV.id == cv_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get CV with details {cv_id}",
                context={"cv_id": cv_id},
                original_error=e
            )

    async def get_latest_by_user(self, user_id: int) -> Optional[CV]:
        """Get user's latest CV.
        
        Args:
            user_id: User ID
            
        Returns:
            Latest CV if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(CV)
                .where(CV.user_id == user_id)
                .order_by(desc(CV.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get latest CV for user {user_id}",
                context={"user_id": user_id},
                original_error=e
            )

    async def create_cv(
        self,
        user_id: int,
        original_filename: str,
        file_path: str,
        content_type: str,
        file_size: int
    ) -> CV:
        """Create new CV record.
        
        Args:
            user_id: User ID
            original_filename: Original filename
            file_path: Path where file is stored
            content_type: File content type
            file_size: File size in bytes
            
        Returns:
            Created CV
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            now = datetime.now(timezone.utc)
            return await self.create(
                user_id=user_id,
                original_filename=original_filename,
                file_path=file_path,
                content_type=content_type,
                file_size=file_size,
                created_at=now,
                updated_at=now
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create CV for user {user_id}",
                context={
                    "user_id": user_id,
                    "original_filename": original_filename
                },
                original_error=e
            )

    async def update_extracted_data(
        self,
        cv_id: int,
        raw_text: str,
        structured_data: Dict,
        embedding: List[float],
        skills: List[str]
    ) -> CV:
        """Update CV with extracted data.
        
        Args:
            cv_id: CV ID
            raw_text: Extracted text from CV
            structured_data: Structured CV data
            embedding: CV text embedding vector
            skills: Extracted skills
            
        Returns:
            Updated CV
            
        Raises:
            UserError: If CV not found
            DatabaseError: If database operation fails
        """
        try:
            cv = await self.get(cv_id)
            if not cv:
                raise UserError(
                    message=f"CV {cv_id} not found"
                )

            cv.raw_text = raw_text
            cv.structured_data = structured_data
            cv.embedding = embedding
            cv.skills = skills
            cv.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return cv
        except UserError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update extracted data for CV {cv_id}",
                context={"cv_id": cv_id},
                original_error=e
            )

    async def add_experience(
        self,
        cv_id: int,
        company: str,
        title: str,
        location: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_current: bool = False,
        description: Optional[str] = None,
        skills: Optional[List[str]] = None
    ) -> CVExperience:
        """Add work experience to CV.
        
        Args:
            cv_id: CV ID
            company: Company name
            title: Job title
            location: Optional job location
            start_date: Optional start date
            end_date: Optional end date
            is_current: Whether this is current job
            description: Optional job description
            skills: Optional list of skills
            
        Returns:
            Created experience record
            
        Raises:
            UserError: If CV not found
            DatabaseError: If database operation fails
        """
        try:
            cv = await self.get(cv_id)
            if not cv:
                raise UserError(
                    message=f"CV {cv_id} not found"
                )

            experience = CVExperience(
                cv_id=cv_id,
                company=company,
                title=title,
                location=location,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                description=description,
                skills=skills,
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(experience)
            await self.session.commit()
            return experience
        except UserError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to add experience to CV {cv_id}",
                context={
                    "cv_id": cv_id,
                    "company": company,
                    "title": title
                },
                original_error=e
            )

    async def add_education(
        self,
        cv_id: int,
        institution: str,
        degree: str,
        field_of_study: Optional[str] = None,
        location: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_current: bool = False,
        grade: Optional[str] = None,
        activities: Optional[List[str]] = None
    ) -> CVEducation:
        """Add education to CV.
        
        Args:
            cv_id: CV ID
            institution: Institution name
            degree: Degree name
            field_of_study: Optional field of study
            location: Optional location
            start_date: Optional start date
            end_date: Optional end date
            is_current: Whether this is current education
            grade: Optional grade achieved
            activities: Optional list of activities
            
        Returns:
            Created education record
            
        Raises:
            UserError: If CV not found
            DatabaseError: If database operation fails
        """
        try:
            cv = await self.get(cv_id)
            if not cv:
                raise UserError(
                    message=f"CV {cv_id} not found"
                )

            education = CVEducation(
                cv_id=cv_id,
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                location=location,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                grade=grade,
                activities=activities,
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(education)
            await self.session.commit()
            return education
        except UserError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to add education to CV {cv_id}",
                context={
                    "cv_id": cv_id,
                    "institution": institution,
                    "degree": degree
                },
                original_error=e
            )

    async def get_cvs_without_embeddings(
        self,
        limit: int = 100
    ) -> List[CV]:
        """Get CVs that need embeddings generated.
        
        Args:
            limit: Maximum number of CVs to return
            
        Returns:
            List of CVs without embeddings
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(CV)
                .where(CV.embedding.is_(None))
                .where(CV.raw_text.isnot(None))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(
                message="Failed to get CVs without embeddings",
                context={"limit": limit},
                original_error=e
            )

    async def find_similar_cvs(
        self,
        embedding: List[float],
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> List[Tuple[CV, float]]:
        """Find CVs similar to given embedding.
        
        Args:
            embedding: Query embedding vector
            min_similarity: Minimum cosine similarity score
            limit: Maximum number of results
            
        Returns:
            List of (CV, similarity_score) tuples
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Using pgvector's <=> operator for cosine distance
            result = await self.session.execute(
                select(CV, func.cosine_similarity(CV.embedding, embedding).label("similarity"))
                .where(CV.embedding.isnot(None))
                .where(func.cosine_similarity(CV.embedding, embedding) >= min_similarity)
                .order_by(desc("similarity"))
                .limit(limit)
            )
            return [(cv, float(similarity)) for cv, similarity in result.all()]
        except Exception as e:
            raise DatabaseError(
                message="Failed to find similar CVs",
                context={
                    "min_similarity": min_similarity,
                    "limit": limit
                },
                original_error=e
            )
