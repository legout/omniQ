"""
SQLite backend implementation for OmniQ.

This module provides a unified SQLite backend that creates and manages
all storage components (task queue, result storage, event storage) using
a single SQLite database.
"""

from typing import Optional
from pathlib import Path

from ..storage.sqlite import (
    AsyncSQLiteQueue,
    SQLiteQueue,
    AsyncSQLiteResultStorage,
    SQLiteResultStorage,
    AsyncSQLiteEventStorage,
    SQLiteEventStorage,
    AsyncSQLiteScheduleStorage,
    SQLiteScheduleStorage,
)
from ..models.config import SQLiteConfig


class SQLiteBackend:
    """
    SQLite backend that provides unified access to all storage components.
    
    This class creates and manages SQLite-based implementations for:
    - Task queue
    - Result storage  
    - Event storage
    
    All components share the same SQLite database file for consistency
    and simplified configuration.
    """
    
    def __init__(
        self,
        database_path: str = "omniq.db",
        config: Optional[SQLiteConfig] = None,
        **kwargs
    ):
        """
        Initialize SQLite backend.
        
        Args:
            database_path: Path to the SQLite database file
            config: SQLite configuration object
            **kwargs: Additional configuration options
        """
        self.database_path = Path(database_path)
        self.config: SQLiteConfig = config or SQLiteConfig()
        
        # Override config with any provided kwargs
        if kwargs:
            config_dict = self.config.to_dict()
            config_dict.update(kwargs)
            self.config = SQLiteConfig.from_dict(config_dict)
        
        # Use database_path from config if provided
        self.database_path = Path(self.config.database_path)
        
        # Create database directory if it doesn't exist
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage components
        self._task_queue: Optional[AsyncSQLiteQueue] = None
        self._sync_task_queue: Optional[SQLiteQueue] = None
        self._result_storage: Optional[AsyncSQLiteResultStorage] = None
        self._sync_result_storage: Optional[SQLiteResultStorage] = None
        self._event_storage: Optional[AsyncSQLiteEventStorage] = None
        self._sync_event_storage: Optional[SQLiteEventStorage] = None
        self._schedule_storage: Optional[AsyncSQLiteScheduleStorage] = None
        self._sync_schedule_storage: Optional[SQLiteScheduleStorage] = None
    
    def get_task_queue(self, async_mode: bool = True) -> AsyncSQLiteQueue:
        """
        Get the task queue instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Task queue instance
        """
        if async_mode:
            if self._task_queue is None:
                self._task_queue = AsyncSQLiteQueue(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._task_queue
        else:
            if self._sync_task_queue is None:
                self._sync_task_queue = SQLiteQueue(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._sync_task_queue
    
    def get_result_storage(self, async_mode: bool = True) -> AsyncSQLiteResultStorage:
        """
        Get the result storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Result storage instance
        """
        if async_mode:
            if self._result_storage is None:
                self._result_storage = AsyncSQLiteResultStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._result_storage
        else:
            if self._sync_result_storage is None:
                self._sync_result_storage = SQLiteResultStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._sync_result_storage
    
    def get_event_storage(self, async_mode: bool = True) -> AsyncSQLiteEventStorage:
        """
        Get the event storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Event storage instance
        """
        if async_mode:
            if self._event_storage is None:
                self._event_storage = AsyncSQLiteEventStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._event_storage
        else:
            if self._sync_event_storage is None:
                self._sync_event_storage = SQLiteEventStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._sync_event_storage
    
    def get_schedule_storage(self, async_mode: bool = True) -> AsyncSQLiteScheduleStorage:
        """
        Get the schedule storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Schedule storage instance
        """
        if async_mode:
            if self._schedule_storage is None:
                self._schedule_storage = AsyncSQLiteScheduleStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._schedule_storage
        else:
            if self._sync_schedule_storage is None:
                self._sync_schedule_storage = SQLiteScheduleStorage(
                    database_path=str(self.database_path),
                    timeout=self.config.timeout,
                    check_same_thread=self.config.check_same_thread,
                )
            return self._sync_schedule_storage
    
    async def connect_all(self) -> None:
        """Connect all storage components."""
        if self._task_queue:
            await self._task_queue.connect()
        if self._result_storage:
            await self._result_storage.connect()
        if self._event_storage:
            await self._event_storage.connect()
        if self._schedule_storage:
            await self._schedule_storage.connect()
    
    async def disconnect_all(self) -> None:
        """Disconnect all storage components."""
        if self._task_queue:
            await self._task_queue.disconnect()
        if self._result_storage:
            await self._result_storage.disconnect()
        if self._event_storage:
            await self._event_storage.disconnect()
        if self._schedule_storage:
            await self._schedule_storage.disconnect()
    
    def connect_all_sync(self) -> None:
        """Connect all sync storage components."""
        if self._sync_task_queue:
            self._sync_task_queue.connect_sync()
        if self._sync_result_storage:
            self._sync_result_storage.connect_sync()
        if self._sync_event_storage:
            self._sync_event_storage.connect_sync()
        if self._sync_schedule_storage:
            self._sync_schedule_storage.connect_sync()
    
    def disconnect_all_sync(self) -> None:
        """Disconnect all sync storage components."""
        if self._sync_task_queue:
            self._sync_task_queue.disconnect_sync()
        if self._sync_result_storage:
            self._sync_result_storage.disconnect_sync()
        if self._sync_event_storage:
            self._sync_event_storage.disconnect_sync()
        if self._sync_schedule_storage:
            self._sync_schedule_storage.disconnect_sync()
    
    async def cleanup_expired(self) -> dict:
        """
        Clean up expired tasks, results, and schedules.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "expired_tasks": 0,
            "expired_results": 0,
            "expired_schedules": 0,
        }
        
        if self._task_queue:
            stats["expired_tasks"] = await self._task_queue.cleanup_expired_tasks()
        
        if self._result_storage:
            stats["expired_results"] = await self._result_storage.cleanup_expired_results()
        
        if self._schedule_storage:
            stats["expired_schedules"] = await self._schedule_storage.cleanup_expired_schedules()
        
        return stats
    
    def cleanup_expired_sync(self) -> dict:
        """
        Clean up expired tasks, results, and schedules (sync).
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "expired_tasks": 0,
            "expired_results": 0,
            "expired_schedules": 0,
        }
        
        if self._sync_task_queue:
            stats["expired_tasks"] = self._sync_task_queue.cleanup_expired_tasks_sync()
        
        if self._sync_result_storage:
            stats["expired_results"] = self._sync_result_storage.cleanup_expired_results_sync()
        
        if self._sync_schedule_storage:
            stats["expired_schedules"] = self._sync_schedule_storage.cleanup_expired_schedules_sync()
        
        return stats
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_all()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_all_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_all_sync()
    
    @classmethod
    def from_config(cls, config: SQLiteConfig) -> "SQLiteBackend":
        """
        Create SQLite backend from configuration.
        
        Args:
            config: SQLite configuration
            
        Returns:
            SQLite backend instance
        """
        return cls(
            database_path=config.database_path,
            config=config
        )
    
    @classmethod
    def from_url(cls, url: str) -> "SQLiteBackend":
        """
        Create SQLite backend from URL.
        
        Args:
            url: SQLite database URL (e.g., "sqlite:///path/to/db.sqlite")
            
        Returns:
            SQLite backend instance
        """
        if url.startswith("sqlite:///"):
            database_path = url[10:]  # Remove "sqlite:///" prefix
        elif url.startswith("sqlite://"):
            database_path = url[9:]   # Remove "sqlite://" prefix
        else:
            database_path = url
        
        return cls(database_path=database_path)
    
    def __repr__(self) -> str:
        """String representation of the backend."""
        return f"SQLiteBackend(database_path='{self.database_path}')"