"""Helper functions for task tests."""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv import CV
from app.models.job import Job
from app.models.user import User


async def create_test_users(
    db: AsyncSession,
    count: int = 3,
    days_since_active: Optional[int] = None
) -> List[User]:
    """Create test users.
    
    Args:
        db: Database session
        count: Number of users to create
        days_since_active: Optional days since last activity
        
    Returns:
        List of created users
    """
    users = []
    for i in range(count):
        last_active = None
        if days_since_active is not None:
            last_active = datetime.utcnow() - timedelta(days=days_since_active)
            
        user = User(
            telegram_id=1000 + i,
            username=f"test_user_{i}",
            first_name=f"Test{i}",
            last_name="User",
            last_active_at=last_active
        )
        db.add(user)
        users.append(user)
    
    await db.commit()
    return users


async def create_test_cvs(
    db: AsyncSession,
    users: List[User],
    days_old: Optional[int] = None
) -> List[CV]:
    """Create test CVs.
    
    Args:
        db: Database session
        users: List of users to create CVs for
        days_old: Optional age of CVs in days
        
    Returns:
        List of created CVs
    """
    cvs = []
    for i, user in enumerate(users):
        created_at = None
        if days_old is not None:
            created_at = datetime.utcnow() - timedelta(days=days_old)
            
        cv = CV(
            user_id=user.id,
            file_path=f"/tmp/test_cv_{i}.pdf",
            status="processed",
            created_at=created_at,
            extracted_text=f"Test CV {i} content",
            analysis={
                "skills": ["Python", "SQL"],
                "experience": f"{i+1} years",
                "education": "Bachelor's"
            },
            embedding=[0.1 * i, 0.2 * i, 0.3 * i]
        )
        db.add(cv)
        cvs.append(cv)
    
    await db.commit()
    return cvs


async def create_test_jobs(
    db: AsyncSession,
    count: int = 3,
    days_old: Optional[int] = None,
    status: str = "active"
) -> List[Job]:
    """Create test jobs.
    
    Args:
        db: Database session
        count: Number of jobs to create
        days_old: Optional age of jobs in days
        status: Job status
        
    Returns:
        List of created jobs
    """
    jobs = []
    for i in range(count):
        posted_at = None
        if days_old is not None:
            posted_at = datetime.utcnow() - timedelta(days=days_old)
            
        job = Job(
            job_title=f"Test Job {i}",
            company_name=f"Company {i}",
            location="London",
            description=f"Test job {i} description",
            requirements=f"Test job {i} requirements",
            status=status,
            posted_at=posted_at,
            embedding=[0.1 * i, 0.2 * i, 0.3 * i]
        )
        db.add(job)
        jobs.append(job)
    
    await db.commit()
    return jobs


async def wait_for_task(task_id: str, timeout: int = 5) -> Dict[str, Any]:
    """Wait for a task to complete.
    
    Args:
        task_id: ID of the task to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        Task result
        
    Raises:
        TimeoutError: If task doesn't complete within timeout
        Exception: If task fails
    """
    start_time = datetime.utcnow()
    while True:
        # Check if task is done
        result = await AsyncResult(task_id).get(timeout=1)
        if result is not None:
            return result
            
        # Check timeout
        if (datetime.utcnow() - start_time).total_seconds() > timeout:
            raise TimeoutError(f"Task {task_id} didn't complete within {timeout} seconds")
            
        # Wait before checking again
        await asyncio.sleep(0.1)
