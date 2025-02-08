"""Vector search service for semantic similarity matching."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import ARRAY, DateTime, Float, Integer, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DatabaseError, OpenAIError
from app.models.cv import CV
from app.models.job import Job
from app.repositories.cv import CVRepository
from app.repositories.job import JobRepository
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector-based semantic search operations."""

    def __init__(self, db: AsyncSession, openai: Optional[OpenAIService] = None) -> None:
        """Initialize service.

        Args:
            db: Database session
            openai: Optional OpenAI service (for testing)
        """
        self.db = db
        self.openai = openai or OpenAIService()
        self.cv_repo = CVRepository(db)
        self.job_repo = JobRepository(db)

    async def find_matching_jobs(
        self, cv_id: int, min_score: float = 0.7, limit: int = 10
    ) -> List[Dict]:
        """Find jobs matching a CV using vector similarity.

        Args:
            cv_id: CV ID to match against
            min_score: Minimum similarity score (0-1)
            limit: Maximum number of results

        Returns:
            List of matching jobs with scores

        Raises:
            DatabaseError: If database operation fails
            ValueError: If CV not found or has no embedding
        """
        try:
            # Get CV with embedding
            cv = await self.cv_repo.get(cv_id, load_relationships=["embedding"])
            if not cv:
                raise ValueError(f"CV {cv_id} not found")

            if not cv.embedding:
                raise ValueError(f"CV {cv_id} has no embedding")

            # Validate embedding
            embedding = cv.embedding.embedding
            if not isinstance(embedding, list) or len(embedding) != 1536:
                raise ValueError(
                    f"Invalid embedding format: expected list of 1536 dimensions, "
                    f"got {type(embedding)} with "
                    f"{len(embedding) if isinstance(embedding, list) else 'unknown'} "
                    "dimensions"
                )

            # Convert embedding to array literal
            embedding_array = f"[{','.join(str(x) for x in embedding)}]"

            # Find similar jobs using cosine distance
            query = text(
                """
                SELECT
                    j.*,
                    1 - (je.embedding::vector <=> $1::vector) as similarity_score
                FROM "JobsApp_job" j
                JOIN job_embeddings je ON je.job_id = j.id
                WHERE j.is_indexed = true
                AND je.embedding IS NOT NULL
                AND 1 - (je.embedding::vector <=> $1::vector) >= $2
                ORDER BY similarity_score DESC
                LIMIT $3;
                """
            )

            # Execute query with parameters
            result = await self.db.execute(query, (embedding_array, min_score, limit))

            matches = []
            for row in result:
                job_dict = dict(row._mapping)
                score = job_dict.pop("similarity_score")
                matches.append({"job": job_dict, "score": float(score)})

            logger.info(
                "Successfully found matching jobs",
                extra={
                    "cv_id": cv_id,
                    "embedding_dim": len(embedding),
                    "min_score": min_score,
                    "limit": limit,
                    "matches_found": len(matches),
                },
            )

            return matches

        except ValueError as e:
            # Re-raise ValueError with same message
            raise

        except Exception as e:
            logger.error(
                "Failed to find matching jobs",
                extra={
                    "cv_id": cv_id,
                    "min_score": min_score,
                    "limit": limit,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            raise DatabaseError(
                message="Failed to find matching jobs",
                context={
                    "cv_id": cv_id,
                    "min_score": min_score,
                    "limit": limit,
                    "error_type": type(e).__name__,
                },
                original_error=e,
            )

    async def find_matching_cvs(
        self, job_id: int, min_score: float = 0.7, limit: int = 10
    ) -> List[Dict]:
        """Find CVs matching a job using vector similarity.

        Args:
            job_id: Job ID to match against
            min_score: Minimum similarity score (0-1)
            limit: Maximum number of results

        Returns:
            List of matching CVs with scores

        Raises:
            DatabaseError: If database operation fails
            ValueError: If job not found or has no embedding
        """
        try:
            # Get job with embedding
            job = await self.job_repo.get(job_id, load_relationships=["embedding"])
            if not job:
                raise ValueError(f"Job {job_id} not found")

            if not job.embedding:
                raise ValueError(f"Job {job_id} has no embedding")

            # Validate embedding
            embedding = job.embedding.embedding
            if not isinstance(embedding, list) or len(embedding) != 1536:
                raise ValueError(
                    f"Invalid embedding format: expected list of 1536 dimensions, "
                    f"got {type(embedding)} with "
                    f"{len(embedding) if isinstance(embedding, list) else 'unknown'} "
                    "dimensions"
                )

            # Convert embedding to array literal
            embedding_array = f"[{','.join(str(x) for x in embedding)}]"

            # Find similar CVs using cosine distance
            query = text(
                """
                SELECT
                    c.*,
                    1 - (ce.embedding::vector <=> $1::vector) as similarity_score
                FROM cvs c
                JOIN cv_embeddings ce ON ce.cv_id = c.id
                WHERE ce.embedding IS NOT NULL
                AND 1 - (ce.embedding::vector <=> $1::vector) >= $2
                ORDER BY similarity_score DESC
                LIMIT $3;
                """
            )

            # Execute query with parameters
            result = await self.db.execute(query, (embedding_array, min_score, limit))

            matches = []
            for row in result:
                cv_dict = dict(row._mapping)
                score = cv_dict.pop("similarity_score")
                matches.append({"cv": cv_dict, "score": float(score)})

            logger.info(
                "Successfully found matching CVs",
                extra={
                    "job_id": job_id,
                    "embedding_dim": len(embedding),
                    "min_score": min_score,
                    "limit": limit,
                    "matches_found": len(matches),
                },
            )

            return matches

        except ValueError as e:
            # Re-raise ValueError with same message
            raise

        except Exception as e:
            logger.error(
                "Failed to find matching CVs",
                extra={
                    "job_id": job_id,
                    "min_score": min_score,
                    "limit": limit,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            raise DatabaseError(
                message="Failed to find matching CVs",
                context={
                    "job_id": job_id,
                    "min_score": min_score,
                    "limit": limit,
                    "error_type": type(e).__name__,
                },
                original_error=e,
            )

    async def update_job_embedding(self, job_id: int) -> None:
        """Update job embedding.

        Args:
            job_id: Job ID to update

        Raises:
            DatabaseError: If database operation fails
            OpenAIError: If embedding generation fails
            ValueError: If job not found
        """
        try:
            # Get job
            job = await self.job_repo.get(job_id, load_relationships=["embedding"])
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Generate embedding
            embedding = await self.openai.generate_embedding(job.description)

            # Validate embedding
            if not isinstance(embedding, list) or len(embedding) != 1536:
                raise ValueError(
                    f"Invalid embedding format from OpenAI: expected list of 1536 dimensions, "
                    f"got {type(embedding)} with "
                    f"{len(embedding) if isinstance(embedding, list) else 'unknown'} "
                    "dimensions"
                )

            # Update job embedding
            query = text(
                """
                INSERT INTO job_embeddings (job_id, embedding)
                VALUES (:job_id, :embedding)
                ON CONFLICT (job_id)
                DO UPDATE SET
                    embedding = :embedding,
                    updated_at = CURRENT_TIMESTAMP;
                """
            ).bindparams(
                bindparam("job_id", type_=Integer),
                bindparam("embedding", type_=ARRAY(Float)),
            )

            await self.db.execute(
                query,
                {
                    "job_id": job_id,
                    "embedding": embedding,
                },
            )

            logger.info(
                "Successfully updated job embedding",
                extra={
                    "job_id": job_id,
                    "embedding_dim": len(embedding),
                },
            )

        except Exception as e:
            logger.error(
                "Failed to update job embedding",
                extra={
                    "job_id": job_id,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            raise DatabaseError(
                message="Failed to update job embedding",
                context={"job_id": job_id},
                original_error=e,
            )

    async def update_cv_embedding(self, cv_id: int) -> None:
        """Update CV embedding.

        Args:
            cv_id: CV ID to update

        Raises:
            DatabaseError: If database operation fails
            OpenAIError: If embedding generation fails
            ValueError: If CV not found
        """
        try:
            # Get CV
            cv = await self.cv_repo.get(cv_id, load_relationships=["embedding"])
            if not cv:
                raise ValueError(f"CV {cv_id} not found")

            # Generate embedding
            embedding = await self.openai.generate_embedding(cv.raw_text)

            # Validate embedding
            if not isinstance(embedding, list) or len(embedding) != 1536:
                raise ValueError(
                    f"Invalid embedding format from OpenAI: expected list of 1536 dimensions, "
                    f"got {type(embedding)} with "
                    f"{len(embedding) if isinstance(embedding, list) else 'unknown'} "
                    "dimensions"
                )

            # Update CV embedding
            query = text(
                """
                INSERT INTO cv_embeddings (cv_id, embedding)
                VALUES (:cv_id, :embedding)
                ON CONFLICT (cv_id)
                DO UPDATE SET
                    embedding = :embedding,
                    updated_at = CURRENT_TIMESTAMP;
                """
            ).bindparams(
                bindparam("cv_id", type_=Integer),
                bindparam("embedding", type_=ARRAY(Float)),
            )

            await self.db.execute(
                query,
                {
                    "cv_id": cv_id,
                    "embedding": embedding,
                },
            )

            logger.info(
                "Successfully updated CV embedding",
                extra={
                    "cv_id": cv_id,
                    "embedding_dim": len(embedding),
                },
            )

        except Exception as e:
            logger.error(
                "Failed to update CV embedding",
                extra={
                    "cv_id": cv_id,
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )
            raise DatabaseError(
                message="Failed to update CV embedding",
                context={"cv_id": cv_id},
                original_error=e,
            )

    async def refresh_job_matches(
        self, user_id: int, min_score: float = 0.7, limit: int = 50
    ) -> List[Dict]:
        """Refresh job matches for a user's latest CV.

        Args:
            user_id: User ID
            min_score: Minimum similarity score (0-1)
            limit: Maximum number of matches

        Returns:
            List of job matches

        Raises:
            DatabaseError: If database operation fails
            ValueError: If no CV found
        """
        try:
            # Get user's latest CV
            cv = await self.cv_repo.get_latest_by_user(user_id)
            if not cv:
                return []  # No CV found, return empty matches

            # Find matching jobs
            matches = await self.find_matching_jobs(
                cv.id, min_score=min_score, limit=limit
            )
            return matches

        except Exception as e:
            raise DatabaseError(
                message="Failed to refresh job matches",
                context={"user_id": user_id},
                original_error=e,
            )
