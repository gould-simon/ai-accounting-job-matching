"""Repository for system maintenance operations."""
import logging
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import MaintenanceError
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)


class MaintenanceRepository:
    """Repository for system maintenance operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository.
        
        Args:
            db: Database session
        """
        self.db = db
        self.openai_service = OpenAIService()

    async def cleanup_old_logs(self, days: int) -> int:
        """Delete log entries older than specified days.
        
        Args:
            days: Number of days after which to delete logs
            
        Returns:
            Number of deleted log entries
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                text("""
                    DELETE FROM system_logs
                    WHERE created_at < :cutoff_date
                    RETURNING id
                """),
                {"cutoff_date": cutoff_date}
            )
            
            deleted_rows = result.rowcount
            return deleted_rows
            
        except Exception as e:
            logger.exception("Error cleaning up old logs")
            raise MaintenanceError("Failed to clean up old logs") from e

    async def get_inactive_users(self, days: int) -> List[Dict]:
        """Get users who haven't been active for specified days.
        
        Args:
            days: Number of days of inactivity
            
        Returns:
            List of inactive user records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                text("""
                    SELECT id, telegram_id, username, last_active_at
                    FROM users
                    WHERE last_active_at < :cutoff_date
                    AND status != 'archived'
                """),
                {"cutoff_date": cutoff_date}
            )
            
            return result.fetchall()
            
        except Exception as e:
            logger.exception("Error getting inactive users")
            raise MaintenanceError("Failed to get inactive users") from e

    async def archive_user_data(self, user_id: int) -> None:
        """Archive data for an inactive user.
        
        Args:
            user_id: ID of the user to archive
        """
        try:
            # Archive user record
            await self.db.execute(
                text("""
                    UPDATE users
                    SET status = 'archived',
                        archived_at = :archived_at
                    WHERE id = :user_id
                """),
                {
                    "user_id": user_id,
                    "archived_at": datetime.utcnow()
                }
            )
            
            # Archive user's CVs
            await self.db.execute(
                text("""
                    UPDATE cvs
                    SET status = 'archived',
                        archived_at = :archived_at
                    WHERE user_id = :user_id
                """),
                {
                    "user_id": user_id,
                    "archived_at": datetime.utcnow()
                }
            )
            
            # Archive user's job matches
            await self.db.execute(
                text("""
                    UPDATE job_matches
                    SET status = 'archived',
                        archived_at = :archived_at
                    WHERE user_id = :user_id
                """),
                {
                    "user_id": user_id,
                    "archived_at": datetime.utcnow()
                }
            )
            
        except Exception as e:
            logger.exception(f"Error archiving user {user_id}")
            raise MaintenanceError(f"Failed to archive user {user_id}") from e

    async def vacuum_analyze(self) -> List[str]:
        """Vacuum analyze database tables.
        
        Returns:
            List of analyzed table names
        """
        try:
            # Get list of tables
            result = await self.db.execute(
                text("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                """)
            )
            
            tables = [row[0] for row in result.fetchall()]
            
            # Vacuum analyze each table
            for table in tables:
                await self.db.execute(
                    text(f"VACUUM ANALYZE {table}")
                )
            
            return tables
            
        except Exception as e:
            logger.exception("Error during vacuum analyze")
            raise MaintenanceError("Failed to vacuum analyze tables") from e

    async def update_statistics(self) -> List[str]:
        """Update database statistics.
        
        Returns:
            List of tables with updated statistics
        """
        try:
            # Get list of tables
            result = await self.db.execute(
                text("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                """)
            )
            
            tables = [row[0] for row in result.fetchall()]
            
            # Update statistics for each table
            for table in tables:
                await self.db.execute(
                    text(f"ANALYZE {table}")
                )
            
            return tables
            
        except Exception as e:
            logger.exception("Error updating statistics")
            raise MaintenanceError("Failed to update statistics") from e

    async def check_table_bloat(self) -> List[Dict]:
        """Check for table bloat.
        
        Returns:
            List of tables with bloat information
        """
        try:
            result = await self.db.execute(
                text("""
                    WITH constants AS (
                        SELECT current_setting('block_size')::numeric AS bs,
                               23 AS hdr,
                               8 AS ma
                    )
                    SELECT
                        schemaname,
                        tablename,
                        ROUND((CASE WHEN avg_row_len > 0
                            THEN bs*tblpages::bigint/avg_row_len
                            ELSE NULL
                        END)::numeric, 2) AS est_rows,
                        ROUND(tblpages::numeric * bs / 1024 / 1024, 2) AS size_mb,
                        ROUND(CASE WHEN tblpages > 0
                            THEN ((tblpages-est_tblpages)::numeric*bs/1024/1024)
                            ELSE 0
                        END, 2) AS bloat_mb
                    FROM (
                        SELECT
                            schemaname, tablename, bs,
                            CEIL((cc.reltuples*((datahdr+ma-
                                (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS est_tblpages,
                            tblpages,
                            CASE WHEN tblpages > 0 AND cc.reltuples > 0
                                THEN cc.relpages::bigint*bs/cc.reltuples
                                ELSE 0
                            END AS avg_row_len
                        FROM (
                            SELECT
                                ma,bs,schemaname,tablename,
                                (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
                                (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2,
                                tblpages,
                                cc.reltuples,cc.relpages
                            FROM (
                                SELECT
                                    schemaname, tablename, hdr, ma, bs,
                                    SUM((1-null_frac)*avg_width) AS datawidth,
                                    MAX(null_frac) AS maxfracsum,
                                    tblpages
                                FROM (
                                    SELECT
                                        s.schemaname,
                                        s.tablename,
                                        s.hdr,
                                        s.ma,
                                        s.bs,
                                        s.null_frac,
                                        s.avg_width,
                                        s.tblpages
                                    FROM (
                                        SELECT
                                            ns.nspname AS schemaname,
                                            ct.relname AS tablename,
                                            hdr,
                                            ma,
                                            bs,
                                            stawidth AS avg_width,
                                            stanullfrac AS null_frac,
                                            ct.relpages AS tblpages
                                        FROM pg_class ct
                                        JOIN pg_namespace ns ON ns.oid = ct.relnamespace
                                        JOIN pg_statistic s ON s.starelid = ct.oid
                                        JOIN constants ON true
                                        WHERE ct.relkind = 'r'
                                    ) s
                                ) s
                                GROUP BY schemaname, tablename, hdr, ma, bs, tblpages
                            ) s2
                            JOIN pg_class cc ON cc.relname = s2.tablename
                        ) s3
                    ) s4
                    WHERE schemaname = 'public'
                    AND bloat_mb > 10
                    ORDER BY bloat_mb DESC
                """)
            )
            
            return [dict(row) for row in result.fetchall()]
            
        except Exception as e:
            logger.exception("Error checking table bloat")
            raise MaintenanceError("Failed to check table bloat") from e

    async def check_database(self) -> Dict:
        """Check database connectivity and health.
        
        Returns:
            Dict containing database health information
        """
        try:
            start_time = datetime.utcnow()
            
            # Check connection
            result = await self.db.execute(text("SELECT 1"))
            assert result.scalar() == 1
            
            # Get database size
            result = await self.db.execute(
                text("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
            )
            db_size = result.scalar()
            
            # Get connection count
            result = await self.db.execute(
                text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
            )
            connection_count = result.scalar()
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "size": db_size,
                "connections": connection_count
            }
            
        except Exception as e:
            logger.exception("Database health check failed")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_openai_api(self) -> Dict:
        """Check OpenAI API connectivity.
        
        Returns:
            Dict containing API health information
        """
        try:
            start_time = datetime.utcnow()
            
            # Test API with a simple embedding
            await self.openai_service.generate_embedding("test")
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time
            }
            
        except Exception as e:
            logger.exception("OpenAI API health check failed")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_disk_space(self) -> Dict:
        """Check disk space usage.
        
        Returns:
            Dict containing disk space information
        """
        try:
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy" if disk.percent < 90 else "warning",
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
            
        except Exception as e:
            logger.exception("Disk space check failed")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_memory_usage(self) -> Dict:
        """Check memory usage.
        
        Returns:
            Dict containing memory usage information
        """
        try:
            memory = psutil.virtual_memory()
            
            return {
                "status": "healthy" if memory.percent < 90 else "warning",
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.free / (1024**3), 2),
                "percent_used": memory.percent
            }
            
        except Exception as e:
            logger.exception("Memory check failed")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_cpu_usage(self) -> Dict:
        """Check CPU usage.
        
        Returns:
            Dict containing CPU usage information
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            return {
                "status": "healthy" if cpu_percent < 90 else "warning",
                "percent_used": cpu_percent,
                "core_count": cpu_count,
                "frequency_mhz": round(cpu_freq.current, 2) if cpu_freq else None
            }
            
        except Exception as e:
            logger.exception("CPU check failed")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
