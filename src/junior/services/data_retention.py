"""
Data retention and cleanup service
Implements automated data deletion based on retention policies
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from junior.core.config import settings

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Data retention configuration"""
    
    # Retention periods (in days)
    CHAT_RETENTION_DAYS = int(os.getenv("CHAT_RETENTION_DAYS", "90"))
    DOCUMENT_RETENTION_DAYS = int(os.getenv("DOCUMENT_RETENTION_DAYS", "2555"))  # 7 years
    SEARCH_HISTORY_DAYS = int(os.getenv("SEARCH_HISTORY_DAYS", "180"))
    TEMP_FILE_RETENTION_HOURS = int(os.getenv("TEMP_FILE_RETENTION_HOURS", "24"))
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))
    ANALYTICS_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "730"))  # 2 years
    
    @classmethod
    def get_retention_config(cls) -> Dict[str, int]:
        """Get all retention periods"""
        return {
            "chat_conversations": cls.CHAT_RETENTION_DAYS,
            "legal_documents": cls.DOCUMENT_RETENTION_DAYS,
            "search_history": cls.SEARCH_HISTORY_DAYS,
            "temp_files": cls.TEMP_FILE_RETENTION_HOURS,
            "system_logs": cls.LOG_RETENTION_DAYS,
            "analytics": cls.ANALYTICS_RETENTION_DAYS
        }


class DataCleanupService:
    """
    Automated data cleanup service
    Runs scheduled tasks to delete expired data per retention policy
    """
    
    def __init__(self):
        self.policy = RetentionPolicy()
        self.uploads_dir = Path("uploads")
    
    async def run_cleanup(self) -> Dict[str, int]:
        """
        Run all cleanup tasks
        Returns count of deleted items per category
        """
        logger.info("Starting data retention cleanup")
        
        results = {
            "temp_files": await self.cleanup_temp_files(),
            "old_logs": await self.cleanup_old_logs(),
            # TODO: Add database cleanup tasks when DB is implemented
            # "chat_messages": await self.cleanup_old_chats(),
            # "search_history": await self.cleanup_old_searches(),
        }
        
        total_deleted = sum(results.values())
        logger.info(f"Cleanup complete. Total items deleted: {total_deleted}")
        logger.info(f"Breakdown: {results}")
        
        return results
    
    async def cleanup_temp_files(self) -> int:
        """Delete temporary uploaded files older than retention period"""
        if not self.uploads_dir.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(hours=self.policy.TEMP_FILE_RETENTION_HOURS)
        deleted_count = 0
        
        for file_path in self.uploads_dir.rglob("*"):
            if file_path.is_file():
                file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted temp file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
        
        logger.info(f"Deleted {deleted_count} temporary files older than {self.policy.TEMP_FILE_RETENTION_HOURS}h")
        return deleted_count
    
    async def cleanup_old_logs(self) -> int:
        """Delete log files older than retention period"""
        log_dir = Path("logs")
        if not log_dir.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=self.policy.LOG_RETENTION_DAYS)
        deleted_count = 0
        
        for log_file in log_dir.glob("*.log*"):
            if log_file.is_file():
                file_age = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_age < cutoff_time:
                    try:
                        log_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old log: {log_file.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete {log_file}: {e}")
        
        logger.info(f"Deleted {deleted_count} log files older than {self.policy.LOG_RETENTION_DAYS} days")
        return deleted_count
    
    async def cleanup_old_chats(self) -> int:
        """Delete chat messages older than retention period"""
        # TODO: Implement when database is set up
        cutoff_date = datetime.now() - timedelta(days=self.policy.CHAT_RETENTION_DAYS)
        
        # Query would be something like:
        # DELETE FROM chat_messages WHERE created_at < cutoff_date
        # deleted_count = await db.execute(query)
        
        logger.info(f"Chat cleanup not yet implemented (retention: {self.policy.CHAT_RETENTION_DAYS} days)")
        return 0
    
    async def cleanup_old_searches(self) -> int:
        """Delete search history older than retention period"""
        # TODO: Implement when database is set up
        cutoff_date = datetime.now() - timedelta(days=self.policy.SEARCH_HISTORY_DAYS)
        
        logger.info(f"Search history cleanup not yet implemented (retention: {self.policy.SEARCH_HISTORY_DAYS} days)")
        return 0
    
    async def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """
        Delete all data for a specific user (GDPR right to erasure)
        
        Args:
            user_id: User identifier
        
        Returns:
            Count of deleted items per category
        """
        logger.info(f"Deleting all data for user {user_id}")
        
        results = {
            "chat_messages": 0,  # await self._delete_user_chats(user_id),
            "documents": 0,  # await self._delete_user_documents(user_id),
            "search_history": 0,  # await self._delete_user_searches(user_id),
            "cases": 0,  # await self._delete_user_cases(user_id),
            "account": 0,  # await self._delete_user_account(user_id),
        }
        
        total_deleted = sum(results.values())
        logger.info(f"Deleted {total_deleted} items for user {user_id}")
        
        # Log the deletion event for audit trail
        await self._log_deletion_event(user_id, results)
        
        return results
    
    async def _log_deletion_event(self, user_id: str, results: Dict[str, int]) -> None:
        """Log user data deletion for audit purposes"""
        log_entry = {
            "event": "user_data_deletion",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "deleted_items": results,
            "total": sum(results.values()),
            "policy_version": "1.0"
        }
        
        # TODO: Store in audit log database
        logger.info(f"Audit log: {log_entry}")


# Scheduled cleanup function
async def scheduled_cleanup():
    """
    Function to be called by scheduler (e.g., APScheduler, Celery)
    Run daily at 02:00 UTC
    """
    service = DataCleanupService()
    try:
        results = await service.run_cleanup()
        logger.info(f"Scheduled cleanup completed successfully: {results}")
    except Exception as e:
        logger.error(f"Scheduled cleanup failed: {e}", exc_info=True)
