"""Tests for maintenance tasks."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.models.user import User
from app.tasks.maintenance import (
    cleanup_old_logs,
    cleanup_inactive_users,
    database_maintenance,
    health_check
)


@pytest.mark.asyncio
async def test_cleanup_old_logs(db_session):
    """Test cleaning up old logs."""
    # Setup
    old_date = datetime.utcnow() - timedelta(days=31)
    new_date = datetime.utcnow() - timedelta(days=15)
    
    # Insert test logs
    await db_session.execute(
        text("""
            INSERT INTO system_logs (message, level, created_at)
            VALUES 
                ('Old log 1', 'INFO', :old_date),
                ('Old log 2', 'INFO', :old_date),
                ('New log', 'INFO', :new_date)
        """),
        {
            "old_date": old_date,
            "new_date": new_date
        }
    )
    await db_session.commit()
    
    # Execute
    result = await cleanup_old_logs(30)  # 30 days
    
    # Verify
    assert result["success"] is True
    assert result["deleted_count"] == 2
    
    # Check logs were deleted
    remaining_logs = await db_session.execute(
        text("SELECT COUNT(*) FROM system_logs")
    )
    assert remaining_logs.scalar() == 1


@pytest.mark.asyncio
async def test_cleanup_inactive_users(
    db_session,
    mock_maintenance_repository
):
    """Test cleaning up inactive users."""
    # Setup
    old_date = datetime.utcnow() - timedelta(days=181)
    new_date = datetime.utcnow() - timedelta(days=30)
    
    users = [
        User(
            telegram_id=123,
            last_active_at=old_date,
            status="active"
        ),
        User(
            telegram_id=456,
            last_active_at=old_date,
            status="active"
        ),
        User(
            telegram_id=789,
            last_active_at=new_date,
            status="active"
        )
    ]
    
    for user in users:
        db_session.add(user)
    await db_session.commit()
    
    # Execute
    result = await cleanup_inactive_users(180)  # 180 days
    
    # Verify
    assert result["success"] is True
    assert result["cleaned_count"] == 2
    
    # Check users were archived
    archived_users = await db_session.query(User).filter(
        User.status == "archived"
    ).all()
    assert len(archived_users) == 2
    
    active_users = await db_session.query(User).filter(
        User.status == "active"
    ).all()
    assert len(active_users) == 1
    assert active_users[0].telegram_id == 789


@pytest.mark.asyncio
async def test_database_maintenance(mock_maintenance_repository):
    """Test database maintenance tasks."""
    # Setup
    mock_maintenance_repository.vacuum_analyze.return_value = ["table1", "table2"]
    mock_maintenance_repository.update_statistics.return_value = ["table1", "table2"]
    mock_maintenance_repository.check_table_bloat.return_value = [
        {"table": "table1", "bloat_mb": 100},
        {"table": "table2", "bloat_mb": 50}
    ]
    
    # Execute
    result = await database_maintenance()
    
    # Verify
    assert result["success"] is True
    assert len(result["tables_analyzed"]) == 2
    assert len(result["stats_updated"]) == 2
    assert len(result["bloat_report"]) == 2
    
    # Check all maintenance tasks were called
    mock_maintenance_repository.vacuum_analyze.assert_called_once()
    mock_maintenance_repository.update_statistics.assert_called_once()
    mock_maintenance_repository.check_table_bloat.assert_called_once()


@pytest.mark.asyncio
async def test_health_check(mock_maintenance_repository):
    """Test system health check."""
    # Setup
    mock_maintenance_repository.check_database.return_value = {
        "status": "healthy",
        "response_time": 0.1
    }
    mock_maintenance_repository.check_openai_api.return_value = {
        "status": "healthy",
        "response_time": 0.2
    }
    mock_maintenance_repository.check_disk_space.return_value = {
        "status": "healthy",
        "percent_used": 70
    }
    mock_maintenance_repository.check_memory_usage.return_value = {
        "status": "healthy",
        "percent_used": 60
    }
    mock_maintenance_repository.check_cpu_usage.return_value = {
        "status": "healthy",
        "percent_used": 50
    }
    
    # Execute
    result = await health_check()
    
    # Verify
    assert result["success"] is True
    assert result["database"]["status"] == "healthy"
    assert result["openai_api"]["status"] == "healthy"
    assert result["disk"]["status"] == "healthy"
    assert result["memory"]["status"] == "healthy"
    assert result["cpu"]["status"] == "healthy"
    
    # Check all health checks were called
    mock_maintenance_repository.check_database.assert_called_once()
    mock_maintenance_repository.check_openai_api.assert_called_once()
    mock_maintenance_repository.check_disk_space.assert_called_once()
    mock_maintenance_repository.check_memory_usage.assert_called_once()
    mock_maintenance_repository.check_cpu_usage.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_with_issues(mock_maintenance_repository):
    """Test system health check with issues."""
    # Setup
    mock_maintenance_repository.check_database.return_value = {
        "status": "unhealthy",
        "error": "Connection timeout"
    }
    mock_maintenance_repository.check_openai_api.return_value = {
        "status": "healthy",
        "response_time": 0.2
    }
    mock_maintenance_repository.check_disk_space.return_value = {
        "status": "warning",
        "percent_used": 92
    }
    mock_maintenance_repository.check_memory_usage.return_value = {
        "status": "warning",
        "percent_used": 95
    }
    mock_maintenance_repository.check_cpu_usage.return_value = {
        "status": "healthy",
        "percent_used": 50
    }
    
    # Execute
    result = await health_check()
    
    # Verify
    assert result["success"] is True  # Overall task succeeded
    assert result["database"]["status"] == "unhealthy"
    assert "Connection timeout" in result["database"]["error"]
    assert result["disk"]["status"] == "warning"
    assert result["memory"]["status"] == "warning"
