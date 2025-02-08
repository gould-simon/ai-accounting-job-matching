"""Service for job matching and recommendations."""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Sequence, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    ValidationError,
    UserError,
    JobError,
    safe_execute,
)
from app.database import async_session_factory
from app.models.job import Job
from app.models.user import User
from app.repositories.job import JobMatchRepository, JobRepository
from app.repositories.user import UserRepository
from app.services.base import BaseService
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)


class JobMatchingService(BaseService):
    """Service for matching users with jobs."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        """Initialize service.
        
        Args:
            session: Optional database session. If not provided,
                    one will be created during init()
        """
        super().__init__(session)
        self.job_repo: Optional[JobRepository] = None
        self.job_match_repo: Optional[JobMatchRepository] = None
        self.user_repo: Optional[UserRepository] = None

    async def _init_resources(self) -> None:
        """Initialize repositories and ensure embedding service is ready."""
        if not self.session:
            raise ValueError("Database session is required")
            
        self.job_repo = JobRepository(self.session)
        self.job_match_repo = JobMatchRepository(self.session)
        self.user_repo = UserRepository(self.session)
        
        # Ensure embedding service is initialized
        if not embedding_service.initialized:
            await embedding_service.init()

    async def _cleanup_resources(self) -> None:
        """Cleanup service resources."""
        self.job_repo = None
        self.job_match_repo = None
        self.user_repo = None

    async def _check_health(self) -> bool:
        """Check service health.
        
        Returns:
            True if service is healthy
        """
        if not self.job_repo or not self.job_match_repo or not self.user_repo:
            return False
            
        try:
            # Check database connection
            await self.session.execute("SELECT 1")
            
            # Check embedding service
            if not await embedding_service.health_check():
                return False
                
            return True
            
        except Exception as e:
            logger.error("Health check failed", exc_info=e)
            return False

    async def search_jobs(
        self,
        params: Dict[str, Any],
    ) -> Tuple[Sequence[Job], int]:
        """Search for jobs with filters.
        
        Args:
            params: Search parameters
            
        Returns:
            Tuple of (jobs list, total count)
            
        Raises:
            ValidationError: If search parameters are invalid
            DatabaseError: If database query fails
        """
        if not self.initialized:
            raise RuntimeError("Service not initialized")
            
        if not self.job_repo:
            raise RuntimeError("Job repository not initialized")
            
        try:
            # Validate search params
            if params.get("page", 0) < 1:
                raise ValidationError("Page number must be >= 1")
            if params.get("page_size", 0) < 1:
                raise ValidationError("Page size must be >= 1")

            # Execute search query
            jobs, total = await safe_execute(
                self.job_repo.search_jobs,
                params,
                error_msg="Failed to search jobs"
            )

            return jobs, total

        except SQLAlchemyError as e:
            logger.error(f"Database error in job search: {e}")
            raise DatabaseError("Failed to search jobs", original_error=e)

    async def match_jobs_for_user(
        self,
        telegram_id: int,
        limit: int = 10
    ) -> List[Tuple[Job, float]]:
        """Find best matching jobs for user.
        
        Args:
            telegram_id: User's Telegram ID
            limit: Maximum number of matches to return
            
        Returns:
            List of (job, match score) tuples
            
        Raises:
            UserError: If user not found or data invalid
            DatabaseError: If database query fails
        """
        logger.debug(
            "Starting job matching for user",
            extra={
                "telegram_id": telegram_id,
                "limit": limit,
                "service_initialized": self.initialized,
            }
        )

        try:
            # Get user
            logger.debug(
                "Getting user from database",
                extra={"telegram_id": telegram_id}
            )
            user = await safe_execute(
                self.user_repo.get_by_telegram_id,
                telegram_id,
                error_msg="Failed to get user"
            )
            
            if not user:
                error_msg = f"User {telegram_id} not found"
                logger.warning(error_msg)
                raise UserError(error_msg)

            logger.debug(
                "Retrieved user",
                extra={
                    "telegram_id": telegram_id,
                    "user_id": user.id,
                    "has_cv": bool(user.cv_text),
                    "has_embedding": bool(user.cv_embedding),
                }
            )

            # Get user's CV embedding
            if not user.cv_embedding:
                error_msg = "User has no CV uploaded"
                logger.warning(
                    error_msg,
                    extra={
                        "telegram_id": telegram_id,
                        "user_id": user.id,
                    }
                )
                raise UserError(error_msg)

            # Find matching jobs
            logger.debug(
                "Finding job matches",
                extra={
                    "telegram_id": telegram_id,
                    "user_id": user.id,
                    "embedding_size": len(user.cv_embedding),
                }
            )
            matches = await safe_execute(
                self.job_match_repo.find_matches,
                user.cv_embedding,
                limit=limit,
                error_msg="Failed to find job matches"
            )

            logger.debug(
                "Found job matches",
                extra={
                    "telegram_id": telegram_id,
                    "user_id": user.id,
                    "match_count": len(matches),
                }
            )

            # Get full job details
            job_ids = [job_id for job_id, _ in matches]
            jobs = await safe_execute(
                self.job_repo.get_by_ids,
                job_ids,
                error_msg="Failed to get job details"
            )

            logger.debug(
                "Retrieved job details",
                extra={
                    "telegram_id": telegram_id,
                    "user_id": user.id,
                    "job_count": len(jobs),
                    "job_ids": job_ids,
                }
            )

            # Map jobs to scores
            job_map = {job.id: job for job in jobs}
            results = []
            for job_id, score in matches:
                if job := job_map.get(job_id):
                    results.append((job, score))

            logger.info(
                "Successfully matched jobs for user",
                extra={
                    "telegram_id": telegram_id,
                    "user_id": user.id,
                    "match_count": len(results),
                }
            )

            return results

        except SQLAlchemyError as e:
            logger.error(
                "Database error in job matching",
                extra={
                    "telegram_id": telegram_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise DatabaseError("Failed to match jobs", original_error=e)
        except Exception as e:
            logger.error(
                "Unexpected error in job matching",
                extra={
                    "telegram_id": telegram_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise

    async def save_job_match(
        self,
        telegram_id: int,
        job_id: int,
        score: float
    ) -> None:
        """Save a job match for a user.
        
        Args:
            telegram_id: User's Telegram ID
            job_id: Job ID
            score: Match score
            
        Raises:
            UserError: If user not found
            JobError: If job not found
            DatabaseError: If database operation fails
        """
        try:
            # Get user
            user = await safe_execute(
                self.user_repo.get_by_telegram_id,
                telegram_id,
                error_msg="Failed to get user"
            )
            if not user:
                raise UserError(f"User {telegram_id} not found")

            # Get job
            job = await safe_execute(
                self.job_repo.get_by_id,
                job_id,
                error_msg="Failed to get job"
            )
            if not job:
                raise JobError(f"Job {job_id} not found")

            # Save match
            await safe_execute(
                self.job_match_repo.save_match,
                user.id,
                job.id,
                score,
                error_msg="Failed to save job match"
            )

            logger.info(
                f"Saved job match",
                extra={
                    "user_id": user.id,
                    "job_id": job.id,
                    "score": score
                }
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error saving job match: {e}")
            raise DatabaseError("Failed to save job match", original_error=e)

    async def search_jobs(
        self,
        embedding: list[float],
        preferences: Optional[dict] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search for jobs using embedding and preferences.
        
        Args:
            embedding: CV embedding vector
            preferences: Optional preferences dict with location and service
            limit: Maximum number of results
            
        Returns:
            List of job dictionaries with similarity scores
        """
        if not self.initialized:
            await self.init()
            
        # Get repositories
        job_repo, _, _ = await self._get_repos()
        
        # Get location and service from preferences
        location = preferences.get("location") if preferences else None
        service = preferences.get("service") if preferences else None
        
        # Find similar jobs
        jobs_with_scores = await job_repo.find_similar_jobs(
            embedding=embedding,
            min_similarity=0.7,
            limit=limit,
            location=location,
            service=service,
        )
        
        # Convert to dictionaries
        return [
            {
                "job_id": job.id,
                "job_title": job.job_title,
                "location": job.location,
                "service": job.service,
                "seniority": job.seniority,
                "description": job.description,
                "score": score,
            }
            for job, score in jobs_with_scores
        ]

    async def generate_job_matches(
        self,
        telegram_id: int,
        cv_embedding: list[float],
        preferences: Optional[dict] = None,
    ) -> list[dict]:
        """Generate job matches for a user.
        
        Args:
            telegram_id: User's Telegram ID
            cv_embedding: User's CV embedding
            preferences: Optional preferences dict
            
        Returns:
            List of job match dictionaries
        """
        if not self.initialized:
            await self.init()
            
        # Search for matching jobs
        matches = await self.search_jobs(
            embedding=cv_embedding,
            preferences=preferences,
            limit=50,  # Get more matches initially
        )
        
        # Save matches
        saved_matches = await self.save_job_matches(
            telegram_id=telegram_id,
            matches=matches,
        )
        
        return saved_matches

    async def save_job_matches(
        self,
        telegram_id: int,
        matches: list[dict],
    ) -> list[dict]:
        """Save job matches for a user.
        
        Args:
            telegram_id: User's Telegram ID
            matches: List of job match dictionaries
            
        Returns:
            List of saved job match dictionaries
        """
        if not self.initialized:
            await self.init()
            
        # Get repositories
        _, job_match_repo, _ = await self._get_repos()
        
        saved_matches = []
        for match in matches:
            # Create match
            job_match = await job_match_repo.create_match(
                telegram_id=telegram_id,
                job_id=match["job_id"],
                score=match["score"],
            )
            
            # Add to saved matches
            saved_matches.append({
                "job_id": job_match.job_id,
                "score": job_match.score,
                "job_title": match["job_title"],
                "location": match["location"],
                "service": match["service"],
                "seniority": match["seniority"],
                "description": match["description"],
            })
            
        return saved_matches


class JobRecommendationService:
    """Service for proactive job recommendations."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        """Initialize service.
        
        Args:
            session: Optional database session. If not provided,
                    one will be created during init()
        """
        self.session = session
        self.matching_service: Optional[JobMatchingService] = None
        self.user_repo: Optional[UserRepository] = None

    async def init(self) -> None:
        """Initialize service with database session."""
        try:
            if not self.session:
                # Create session if not provided
                self.session = async_session_factory()

            # Initialize services
            self.matching_service = JobMatchingService(self.session)
            await self.matching_service.init()
            
            # Initialize repositories
            self.user_repo = UserRepository(self.session)
            
            logger.info("Job recommendation service initialized")
                
        except SQLAlchemyError as e:
            logger.error("Failed to initialize job recommendation service", exc_info=e)
            raise DatabaseError(
                message="Failed to initialize job recommendation service",
                error_code="INIT_FAILED"
            ) from e

    async def close(self) -> None:
        """Close database session."""
        if self.matching_service:
            await self.matching_service.close()
        if self.session:
            await self.session.close()

    async def generate_recommendations(
        self,
        telegram_id: int,
        cv_embedding: Optional[list[float]] = None,
        preferences: Optional[dict] = None,
        force: bool = False,
    ) -> list[dict]:
        """Generate job recommendations for a user.
        
        Args:
            telegram_id: User's Telegram ID
            cv_embedding: Optional CV embedding vector. If not provided,
                        will use user's stored CV embedding
            preferences: Optional preferences dict
            force: Whether to force regeneration
            
        Returns:
            List of job recommendations
            
        Raises:
            UserError: If user not found or data invalid
            DatabaseError: If database query fails
        """
        try:
            # Initialize if needed
            if not self.matching_service or not self.user_repo:
                await self.init()
            
            # Get user
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if not user:
                raise UserError(
                    message="User not found",
                    error_code="USER_NOT_FOUND"
                )
                
            # Check if we should generate
            if not force and not self._should_generate_recommendations(user):
                logger.info(f"Skipping recommendations for user {telegram_id}")
                return []
                
            # Use provided embedding or get from user
            embedding = cv_embedding
            if not embedding:
                if not user.cv_embedding:
                    raise UserError(
                        message="No CV embedding found",
                        error_code="NO_CV_EMBEDDING"
                    )
                embedding = user.cv_embedding
                
            # Use provided preferences or get from user
            prefs = preferences or user.preferences or {}
            
            # Generate matches
            matches = await self.matching_service.generate_job_matches(
                telegram_id=telegram_id,
                cv_embedding=embedding,
                preferences=prefs,
            )
            
            return matches
            
        except SQLAlchemyError as e:
            logger.error(f"Database error generating recommendations: {e}")
            raise DatabaseError(
                message="Failed to generate recommendations",
                error_code="DB_ERROR"
            ) from e

    def _should_generate_recommendations(self, user: User) -> bool:
        """Check if we should generate new recommendations.
        
        Args:
            user: User to check
            
        Returns:
            True if should generate
        """
        if not user.last_recommendations:
            return True

        now = datetime.now(timezone.utc)
        hours_since_last = (now - user.last_recommendations).total_seconds() / 3600
        return hours_since_last >= 24  # Generate once per day


# Create service instances
job_matching_service = JobMatchingService()
