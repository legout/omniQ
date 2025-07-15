"""
Storage implementations for OmniQ.
"""

from .base import (
    BaseTaskQueue,
    BaseResultStorage,
    BaseEventStorage,
    BaseScheduleStorage,
)

from .file import (
    AsyncFileQueue,
    FileQueue,
    AsyncFileResultStorage,
    FileResultStorage,
    AsyncFileEventStorage,
    FileEventStorage,
    AsyncFileScheduleStorage,
    FileScheduleStorage,
)

from .redis import (
    AsyncRedisQueue,
    RedisQueue,
    AsyncRedisResultStorage,
    RedisResultStorage,
    AsyncRedisEventStorage,
    RedisEventStorage,
)

from .azure import (
    AsyncAzureQueue,
    AzureQueue,
    AsyncAzureResultStorage,
    AzureResultStorage,
    AsyncAzureEventStorage,
    AzureEventStorage,
    AsyncAzureScheduleStorage,
    AzureScheduleStorage,
)

from .gcs import (
    AsyncGCSQueue,
    GCSQueue,
    AsyncGCSResultStorage,
    GCSResultStorage,
    AsyncGCSEventStorage,
    GCSEventStorage,
    AsyncGCSScheduleStorage,
    GCSScheduleStorage,
)

__all__ = [
    # Base interfaces
    "BaseTaskQueue",
    "BaseResultStorage",
    "BaseEventStorage",
    "BaseScheduleStorage",
    # File storage implementations
    "AsyncFileQueue",
    "FileQueue",
    "AsyncFileResultStorage",
    "FileResultStorage",
    "AsyncFileEventStorage",
    "FileEventStorage",
    "AsyncFileScheduleStorage",
    "FileScheduleStorage",
    # Redis storage implementations
    "AsyncRedisQueue",
    "RedisQueue",
    "AsyncRedisResultStorage",
    "RedisResultStorage",
    "AsyncRedisEventStorage",
    "RedisEventStorage",
    # Azure storage implementations
    "AsyncAzureQueue",
    "AzureQueue",
    "AsyncAzureResultStorage",
    "AzureResultStorage",
    "AsyncAzureEventStorage",
    "AzureEventStorage",
    "AsyncAzureScheduleStorage",
    "AzureScheduleStorage",
    # GCS storage implementations
    "AsyncGCSQueue",
    "GCSQueue",
    "AsyncGCSResultStorage",
    "GCSResultStorage",
    "AsyncGCSEventStorage",
    "GCSEventStorage",
    "AsyncGCSScheduleStorage",
    "GCSScheduleStorage",
]