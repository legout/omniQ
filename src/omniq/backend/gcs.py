"""Google Cloud Storage Backend for OmniQ.

This module provides a unified GCS backend that manages all GCS-based storage components
for tasks, results, events, and schedules using fsspec and gcsfs.
"""

from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from ..storage.gcs import (
    AsyncGCSQueue,
    AsyncGCSResultStorage,
    AsyncGCSEventStorage,
    AsyncGCSScheduleStorage,
    GCSQueue,
    GCSResultStorage,
    GCSEventStorage,
    GCSScheduleStorage,
)
from ..storage.base import (
    BaseTaskQueue,
    BaseResultStorage,
    BaseEventStorage,
    BaseScheduleStorage,
)


class GCSBackend:
    """Unified GCS backend for OmniQ.
    
    This backend provides both async and sync storage interfaces for all OmniQ
    storage types (tasks, results, events, schedules) using Google Cloud Storage.
    
    Args:
        bucket_name: GCS bucket name
        prefix: Optional prefix for all keys (default: "omniq/")
        project: GCP project ID (optional, can use environment/service account)
        token: Path to service account JSON file or token string
        access: Access mode ('read_only', 'read_write', 'full_control')
        consistency: Consistency mode ('md5', 'crc32c', 'size', 'none')
        cache_timeout: Cache timeout in seconds
        **gcs_kwargs: Additional arguments passed to gcsfs.GCSFileSystem
    """
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "omniq/",
        project: Optional[str] = None,
        token: Optional[str] = None,
        access: str = "read_write",
        consistency: str = "md5",
        cache_timeout: int = 300,
        **gcs_kwargs: Any,
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.project = project
        self.token = token
        self.access = access
        self.consistency = consistency
        self.cache_timeout = cache_timeout
        self.gcs_kwargs = gcs_kwargs
        
        # Storage instances (created lazily)
        self._async_task_storage: Optional[AsyncGCSQueue] = None
        self._async_result_storage: Optional[AsyncGCSResultStorage] = None
        self._async_event_storage: Optional[AsyncGCSEventStorage] = None
        self._async_schedule_storage: Optional[AsyncGCSScheduleStorage] = None
        
        self._sync_task_storage: Optional[GCSQueue] = None
        self._sync_result_storage: Optional[GCSResultStorage] = None
        self._sync_event_storage: Optional[GCSEventStorage] = None
        self._sync_schedule_storage: Optional[GCSScheduleStorage] = None
        
        # Track if we're in an async context
        self._async_context_active = False
    
    def _get_storage_kwargs(self) -> Dict[str, Any]:
        """Get common kwargs for storage initialization."""
        return {
            "bucket_name": self.bucket_name,
            "base_prefix": self.prefix,
            "project": self.project,
            "token": self.token,
            "access": self.access,
            "consistency": self.consistency,
            "cache_timeout": self.cache_timeout,
            "gcs_additional_kwargs": self.gcs_kwargs,
        }
    
    # Async storage properties
    @property
    def async_task_storage(self) -> BaseTaskQueue:
        """Get async task storage."""
        if self._async_task_storage is None:
            self._async_task_storage = AsyncGCSQueue(**self._get_storage_kwargs())
        return self._async_task_storage
    
    @property
    def async_result_storage(self) -> BaseResultStorage:
        """Get async result storage."""
        if self._async_result_storage is None:
            self._async_result_storage = AsyncGCSResultStorage(**self._get_storage_kwargs())
        return self._async_result_storage
    
    @property
    def async_event_storage(self) -> BaseEventStorage:
        """Get async event storage."""
        if self._async_event_storage is None:
            self._async_event_storage = AsyncGCSEventStorage(**self._get_storage_kwargs())
        return self._async_event_storage
    
    @property
    def async_schedule_storage(self) -> BaseScheduleStorage:
        """Get async schedule storage."""
        if self._async_schedule_storage is None:
            self._async_schedule_storage = AsyncGCSScheduleStorage(**self._get_storage_kwargs())
        return self._async_schedule_storage
    
    # Sync storage properties
    @property
    def task_storage(self) -> BaseTaskQueue:
        """Get sync task storage."""
        if self._sync_task_storage is None:
            self._sync_task_storage = GCSQueue(**self._get_storage_kwargs())
        return self._sync_task_storage
    
    @property
    def result_storage(self) -> BaseResultStorage:
        """Get sync result storage."""
        if self._sync_result_storage is None:
            self._sync_result_storage = GCSResultStorage(**self._get_storage_kwargs())
        return self._sync_result_storage
    
    @property
    def event_storage(self) -> BaseEventStorage:
        """Get sync event storage."""
        if self._sync_event_storage is None:
            self._sync_event_storage = GCSEventStorage(**self._get_storage_kwargs())
        return self._sync_event_storage
    
    @property
    def schedule_storage(self) -> BaseScheduleStorage:
        """Get sync schedule storage."""
        if self._sync_schedule_storage is None:
            self._sync_schedule_storage = GCSScheduleStorage(**self._get_storage_kwargs())
        return self._sync_schedule_storage
    
    # Async context manager support
    async def __aenter__(self):
        """Enter async context."""
        self._async_context_active = True
        
        # Initialize all async storage instances if they exist
        if self._async_task_storage:
            await self._async_task_storage.__aenter__()
        if self._async_result_storage:
            await self._async_result_storage.__aenter__()
        if self._async_event_storage:
            await self._async_event_storage.__aenter__()
        if self._async_schedule_storage:
            await self._async_schedule_storage.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        self._async_context_active = False
        
        # Clean up all async storage instances
        if self._async_task_storage:
            await self._async_task_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_result_storage:
            await self._async_result_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_event_storage:
            await self._async_event_storage.__aexit__(exc_type, exc_val, exc_tb)
        if self._async_schedule_storage:
            await self._async_schedule_storage.__aexit__(exc_type, exc_val, exc_tb)
    
    # Sync context manager support
    def __enter__(self):
        """Enter sync context."""
        # Initialize all sync storage instances if they exist
        if self._sync_task_storage:
            self._sync_task_storage.__enter__()
        if self._sync_result_storage:
            self._sync_result_storage.__enter__()
        if self._sync_event_storage:
            self._sync_event_storage.__enter__()
        if self._sync_schedule_storage:
            self._sync_schedule_storage.__enter__()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context."""
        # Clean up all sync storage instances
        if self._sync_task_storage:
            self._sync_task_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_result_storage:
            self._sync_result_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_event_storage:
            self._sync_event_storage.__exit__(exc_type, exc_val, exc_tb)
        if self._sync_schedule_storage:
            self._sync_schedule_storage.__exit__(exc_type, exc_val, exc_tb)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"GCSBackend(bucket='{self.bucket_name}', prefix='{self.prefix}')"


# Convenience function for creating GCS backend from config
def create_gcs_backend_from_config(config: Dict[str, Any]) -> GCSBackend:
    """Create GCSBackend from configuration dictionary.
    
    Args:
        config: Configuration dictionary with GCS settings
        
    Returns:
        Configured GCSBackend instance
    """
    return GCSBackend(
        bucket_name=config["bucket_name"],
        prefix=config.get("prefix", "omniq/"),
        project=config.get("project"),
        token=config.get("token"),
        access=config.get("access", "read_write"),
        consistency=config.get("consistency", "md5"),
        cache_timeout=config.get("cache_timeout", 300),
        **config.get("gcs_kwargs", {}),
    )