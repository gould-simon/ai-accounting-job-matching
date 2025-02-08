"""Job and firm repository for database operations."""
import logging
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting_firm import AccountingFirm
from app.models.job import Job
from app.models.job_match import JobMatch
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository[Job]):
    """Repository for job-related database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with Job model."""
        super().__init__(Job, session)

    async def get_with_firm(self, job_id: int) -> Optional[Job]:
        """Get job with firm details.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job with loaded firm if found, None otherwise
        """
        result = await self.session.execute(
            select(Job)
            .options(selectinload(Job.firm))
            .where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def search_jobs(
        self,
        *,
        title: Optional[str] = None,
        location: Optional[str] = None,
        seniority: Optional[str] = None,
        service: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[Sequence[Job], int]:
        """Search jobs with filters.
        
        Args:
            title: Optional job title filter
            location: Optional location filter
            seniority: Optional seniority level filter
            service: Optional service area filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (jobs list, total count)
        """
        # Build query
        query = select(Job).options(selectinload(Job.firm))
        count_query = select(func.count()).select_from(Job)

        # Apply filters
        if title:
            title_filter = Job.job_title.ilike(f"%{title}%")
            query = query.where(title_filter)
            count_query = count_query.where(title_filter)

        if location:
            location_filter = Job.location.ilike(f"%{location}%")
            query = query.where(location_filter)
            count_query = count_query.where(location_filter)

        if seniority:
            seniority_filter = Job.seniority.ilike(f"%{seniority}%")
            query = query.where(seniority_filter)
            count_query = count_query.where(seniority_filter)

        if service:
            service_filter = Job.service.ilike(f"%{service}%")
            query = query.where(service_filter)
            count_query = count_query.where(service_filter)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        result = await self.session.execute(
            query.offset(skip).limit(limit)
        )
        jobs = list(result.scalars().all())

        return jobs, total

    async def find_similar_jobs(
        self,
        embedding: list[float],
        *,
        min_similarity: float = 0.7,
        limit: int = 10,
        location: Optional[str] = None,
        seniority: Optional[str] = None,
        service: Optional[str] = None,
    ) -> list[tuple[Job, float]]:
        """Find jobs with similar embeddings.
        
        Uses pgvector's cosine similarity to find jobs with similar
        embeddings to the provided query embedding.
        
        Args:
            embedding: Query embedding vector
            min_similarity: Minimum cosine similarity threshold (0-1)
            limit: Maximum number of results to return
            location: Optional location filter
            seniority: Optional seniority level filter
            service: Optional service area filter
            
        Returns:
            List of tuples containing (job, similarity_score)
        """
        # Build base query
        query = """
            SELECT j.*, 1 - (je.embedding <=> :embedding) as similarity
            FROM "JobsApp_job" j
            JOIN job_embeddings je ON je.job_id = j.id
            WHERE je.embedding IS NOT NULL
            AND 1 - (je.embedding <=> :embedding) >= :min_similarity
        """
        params = {
            "embedding": embedding,
            "min_similarity": min_similarity
        }

        # Add optional filters
        if location:
            query += "\n AND j.location ILIKE :location"
            params["location"] = f"%{location}%"

        if seniority:
            query += "\n AND j.seniority ILIKE :seniority"
            params["seniority"] = f"%{seniority}%"

        if service:
            query += "\n AND j.service ILIKE :service"
            params["service"] = f"%{service}%"

        # Add ordering and limit
        query += """
            ORDER BY similarity DESC
            LIMIT :limit
        """
        params["limit"] = limit

        # Execute query
        result = await self.session.execute(query, params)
        rows = await result.all()

        # Convert to list of (Job, similarity) tuples
        jobs_with_scores = [
            (Job(**row._mapping), float(row.similarity))
            for row in rows
        ]

        return jobs_with_scores

    async def get_jobs_without_embeddings(
        self,
        limit: int = 100
    ) -> list[Job]:
        """Get jobs that don't have embeddings yet.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs without embeddings
        """
        result = await self.session.execute(
            select(Job)
            .where(Job.embedding.is_(None))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_embedding(
        self,
        job_id: int,
        embedding: list[float]
    ) -> None:
        """Update job embedding.
        
        Args:
            job_id: Job ID
            embedding: New embedding vector
        """
        job = await self.get(job_id)
        if job:
            job.embedding = embedding
            await self.session.commit()

    async def get_recent_jobs(
        self,
        *,
        days: int = 7,
        limit: int = 10
    ) -> list[Job]:
        """Get recently posted jobs.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of jobs to return
            
        Returns:
            List of recent jobs
        """
        cutoff_date = date.today() - date.timedelta(days=days)
        result = await self.session.execute(
            select(Job)
            .where(Job.created_at >= cutoff_date)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class JobMatchRepository(BaseRepository[JobMatch]):
    """Repository for job match operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with JobMatch model."""
        super().__init__(JobMatch, session)

    async def create_match(
        self,
        telegram_id: int,
        job_id: int,
        score: float,
    ) -> JobMatch:
        """Create new job match.
        
        Args:
            telegram_id: Telegram user ID
            job_id: Job ID
            score: Match score
            
        Returns:
            Created job match
        """
        return await self.create(
            telegram_id=telegram_id,
            job_id=job_id,
            score=score,
        )

    async def get_user_matches(
        self,
        telegram_id: int,
        limit: int = 10,
    ) -> list[JobMatch]:
        """Get user's job matches.
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of matches to return
            
        Returns:
            List of job matches
        """
        result = await self.session.execute(
            select(JobMatch)
            .options(selectinload(JobMatch.job).selectinload(Job.firm))
            .where(JobMatch.telegram_id == telegram_id)
            .order_by(JobMatch.score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
