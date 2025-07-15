"""S3 Backend for OmniQ.

This module provides a unified S3 backend that manages all S3-based storage components
for tasks, results, events, and schedules using fsspec and s3fs.
"""

from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from ..storage.s3 import (
    AsyncS3Queue,
    AsyncS3ResultStorage,
    AsyncS3EventStorage,
    AsyncS3ScheduleStorage,
    S3Queue,
    S3ResultStorage,
    S3EventStorage,
    S3ScheduleStorage,
)
from ..storage.base import (
    BaseTaskQueue,
    BaseResultStorage,
    BaseEventStorage,
    BaseScheduleStorage,
)


class S3Backend:
    """Unified S3 backend for OmniQ.
    
    This backend provides both async and sync storage interfaces for all OmniQ
    storage types (tasks, results, events, schedules) using S3-compatible storage.
    
    Args:
        bucket_name: S3 bucket name
        prefix: Optional prefix for all keys (default: "omniq/")
        aws_access_key_id: AWS access key ID (optional, can use environment/IAM)
        aws_secret_access_key: AWS secret access key (optional, can use environment/IAM)
        region_name: AWS region name (default: "us-east-1")
        endpoint_url: Custom S3 endpoint URL for S3-compatible services
        **s3_kwargs: Additional arguments passed to s3fs.S3FileSystem
    """
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "omniq/",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        **s3_kwargs: Any,
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.s3_kwargs = s3_kwargs
        
        # Storage instances (created lazily)
        self._async_task_storage: Optional[AsyncS3Queue] = None
        self._async_result_storage: Optional[AsyncS3ResultStorage] = None
        self._async_event_storage: Optional[AsyncS3EventStorage] = None
        self._async_schedule_storage: Optional[AsyncS3ScheduleStorage] = None
        
        self._sync_task_storage: Optional[S3Queue] = None
        self._sync_result_storage: Optional[S3ResultStorage] = None
        self._sync_event_storage: Optional[S3EventStorage] = None
        self._sync_schedule_storage: Optional[S3ScheduleStorage] = None
        
        # Track if we're in an async context
        self._async_context_active = False
    
    def _get_storage_kwargs(self) -> Dict[str, Any]:
        """Get common kwargs for storage initialization."""
        return {
            "bucket_name": self.bucket_name,
            "prefix": self.prefix,
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
            "region_name": self.region_name,
            "endpoint_url": self.endpoint_url,
            **self.s3_kwargs,
        }
    
    # Async storage properties
    @property
    def async_task_storage(self) -> BaseTaskQueue:
        """Get async task storage."""
        if self._async_task_storage is None:
            self._async_task_storage = AsyncS3Queue(**self._get_storage_kwargs())
        return self._async_task_storage
    
    @property
    def async_result_storage(self) -> BaseResultStorage:
        """Get async result storage."""
        if self._async_result_storage is None:
            self._async_result_storage = AsyncS3ResultStorage(**self._get_storage_kwargs())
        return self._async_result_storage
    
    @property
    def async_event_storage(self) -> BaseEventStorage:
        """Get async event storage."""
        if self._async_event_storage is None:
            self._async_event_storage = AsyncS3EventStorage(**self._get_storage_kwargs())
        return self._async_event_storage
    
    @property
    def async_schedule_storage(self) -> BaseScheduleStorage:
        """Get async schedule storage."""
        if self._async_schedule_storage is None:
            self._async_schedule_storage = AsyncS3ScheduleStorage(**self._get_storage_kwargs())
        return self._async_schedule_storage
    
    # Sync storage properties
    @property
    def task_storage(self) -> BaseTaskQueue:
        """Get sync task storage."""
        if self._sync_task_storage is None:
            self._sync_task_storage = S3Queue(**self._get_storage_kwargs())
        return self._sync_task_storage
    
    @property
    def result_storage(self) -> BaseResultStorage:
        """Get sync result storage."""
        if self._sync_result_storage is None:
            self._sync_result_storage = S3ResultStorage(**self._get_storage_kwargs())
        return self._sync_result_storage
    
    @property
    def event_storage(self) -> BaseEventStorage:
        """Get sync event storage."""
        if self._sync_event_storage is None:
            self._sync_event_storage = S3EventStorage(**self._get_storage_kwargs())
        return self._sync_event_storage
    
    @property
    def schedule_storage(self) -> BaseScheduleStorage:
        """Get sync schedule storage."""
        if self._sync_schedule_storage is None:
            self._sync_schedule_storage = S3ScheduleStorage(**self._get_storage_kwargs())
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
        return f"S3Backend(bucket='{self.bucket_name}', prefix='{self.prefix}')"


# Convenience function for creating S3 backend from config
def create_s3_backend_from_config(config: Dict[str, Any]) -> S3Backend:
    """Create S3Backend from configuration dictionary.
    
    Args:
        config: Configuration dictionary with S3 settings
        
    Returns:
        Configured S3Backend instance
    """
    return S3Backend(
        bucket_name=config["bucket_name"],
        prefix=config.get("prefix", "omniq/"),
        aws_access_key_id=config.get("aws_access_key_id"),
        aws_secret_access_key=config.get("aws_secret_access_key"),
        region_name=config.get("region_name", "us-east-1"),
        endpoint_url=config.get("endpoint_url"),
        **config.get("s3_kwargs", {}),
    )