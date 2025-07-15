"""
File backend implementation for OmniQ.

This module provides a unified file backend that creates and manages
all storage components (task queue, result storage, event storage, schedule storage) 
using fsspec with DirFileSystem for cross-platform file operations.
"""

from typing import Any, Dict, Optional
from pathlib import Path
from urllib.parse import urlparse

from ..storage.file import (
    AsyncFileQueue,
    FileQueue,
    AsyncFileResultStorage,
    FileResultStorage,
    AsyncFileEventStorage,
    FileEventStorage,
    AsyncFileScheduleStorage,
    FileScheduleStorage,
)
from ..models.config import FileConfig


class FileBackend:
    """
    File backend that provides unified access to all storage components.
    
    This class creates and manages file-based implementations for:
    - Task queue
    - Result storage  
    - Event storage
    - Schedule storage
    
    All components share the same base directory and fsspec configuration
    for consistency and simplified configuration.
    """
    
    def __init__(
        self,
        base_dir: str = "omniq_data",
        fs_protocol: str = "file",
        fs_kwargs: Optional[Dict[str, Any]] = None,
        config: Optional[FileConfig] = None,
        **kwargs
    ):
        """
        Initialize file backend.
        
        Args:
            base_dir: Base directory for storing files
            fs_protocol: fsspec protocol (file, s3, gcs, etc.)
            fs_kwargs: Additional kwargs for fsspec filesystem
            config: File configuration object
            **kwargs: Additional configuration options
        """
        self.config: FileConfig = config or FileConfig()
        
        # Override config with any provided kwargs
        if kwargs:
            config_dict = self.config.to_dict()
            config_dict.update(kwargs)
            self.config = FileConfig.from_dict(config_dict)
        
        # Use provided parameters or fall back to config
        self.base_dir = Path(base_dir if base_dir != "omniq_data" else self.config.base_dir)
        self.fs_kwargs = fs_kwargs or self.config.storage_options
        
        # Determine filesystem protocol
        if self.config.fsspec_uri:
            parsed = urlparse(self.config.fsspec_uri)
            self.fs_protocol = parsed.scheme or "file"
            if parsed.path:
                self.base_dir = Path(parsed.path)
        else:
            self.fs_protocol = fs_protocol
        
        # Create base directory if using local filesystem
        if self.fs_protocol == "file":
            self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage components
        self._task_queue: Optional[AsyncFileQueue] = None
        self._sync_task_queue: Optional[FileQueue] = None
        self._result_storage: Optional[AsyncFileResultStorage] = None
        self._sync_result_storage: Optional[FileResultStorage] = None
        self._event_storage: Optional[AsyncFileEventStorage] = None
        self._sync_event_storage: Optional[FileEventStorage] = None
        self._schedule_storage: Optional[AsyncFileScheduleStorage] = None
        self._sync_schedule_storage: Optional[FileScheduleStorage] = None
    
    def get_task_queue(self, async_mode: bool = True):
        """
        Get the task queue instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Task queue instance
        """
        if async_mode:
            if self._task_queue is None:
                self._task_queue = AsyncFileQueue(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._task_queue
        else:
            if self._sync_task_queue is None:
                self._sync_task_queue = FileQueue(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._sync_task_queue
    
    def get_result_storage(self, async_mode: bool = True):
        """
        Get the result storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Result storage instance
        """
        if async_mode:
            if self._result_storage is None:
                self._result_storage = AsyncFileResultStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._result_storage
        else:
            if self._sync_result_storage is None:
                self._sync_result_storage = FileResultStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._sync_result_storage
    
    def get_event_storage(self, async_mode: bool = True):
        """
        Get the event storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Event storage instance
        """
        if async_mode:
            if self._event_storage is None:
                self._event_storage = AsyncFileEventStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._event_storage
        else:
            if self._sync_event_storage is None:
                self._sync_event_storage = FileEventStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._sync_event_storage
    
    def get_schedule_storage(self, async_mode: bool = True):
        """
        Get the schedule storage instance.
        
        Args:
            async_mode: Whether to return async or sync version
            
        Returns:
            Schedule storage instance
        """
        if async_mode:
            if self._schedule_storage is None:
                self._schedule_storage = AsyncFileScheduleStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
                )
            return self._schedule_storage
        else:
            if self._sync_schedule_storage is None:
                self._sync_schedule_storage = FileScheduleStorage(
                    base_dir=str(self.base_dir),
                    fs_protocol=self.fs_protocol,
                    fs_kwargs=self.fs_kwargs,
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
        Clean up expired tasks, results, and events.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "expired_tasks": 0,
            "expired_results": 0,
            "expired_events": 0,
        }
        
        if self._task_queue:
            stats["expired_tasks"] = await self._task_queue.cleanup_expired_tasks()
        
        if self._result_storage:
            stats["expired_results"] = await self._result_storage.cleanup_expired_results()
        
        # Note: File event storage doesn't have expiration cleanup like schedules
        # but we can clean up old events based on timestamp
        
        return stats
    
    def cleanup_expired_sync(self) -> dict:
        """
        Clean up expired tasks, results, and events (sync).
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "expired_tasks": 0,
            "expired_results": 0,
            "expired_events": 0,
        }
        
        if self._sync_task_queue:
            stats["expired_tasks"] = self._sync_task_queue.cleanup_expired_tasks_sync()
        
        if self._sync_result_storage:
            stats["expired_results"] = self._sync_result_storage.cleanup_expired_results_sync()
        
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
    def from_config(cls, config: FileConfig) -> "FileBackend":
        """
        Create file backend from configuration.
        
        Args:
            config: File configuration
            
        Returns:
            File backend instance
        """
        return cls(
            base_dir=config.base_dir,
            config=config
        )
    
    @classmethod
    def from_url(cls, url: str, **kwargs) -> "FileBackend":
        """
        Create file backend from URL.
        
        Args:
            url: File system URL (e.g., "file:///path/to/dir", "s3://bucket/path")
            **kwargs: Additional configuration options
            
        Returns:
            File backend instance
        """
        parsed = urlparse(url)
        fs_protocol = parsed.scheme or "file"
        
        if fs_protocol == "file":
            base_dir = parsed.path or url
        else:
            base_dir = parsed.path.lstrip("/") if parsed.path else ""
        
        # Extract storage options from query parameters
        fs_kwargs = kwargs.copy()
        if parsed.hostname:
            fs_kwargs["host"] = parsed.hostname
        if parsed.port:
            fs_kwargs["port"] = parsed.port
        if parsed.username:
            fs_kwargs["username"] = parsed.username
        if parsed.password:
            fs_kwargs["password"] = parsed.password
        
        return cls(
            base_dir=base_dir,
            fs_protocol=fs_protocol,
            fs_kwargs=fs_kwargs
        )
    
    def __repr__(self) -> str:
        """String representation of the backend."""
        return f"FileBackend(base_dir='{self.base_dir}', fs_protocol='{self.fs_protocol}')"