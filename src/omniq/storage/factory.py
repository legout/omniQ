"""
Storage backend factory for creating individual storage components.

This module provides a factory system for creating storage components
independently, allowing users to mix and match different backends for
different storage types (task queue, result storage, event storage, schedule storage).
"""

from typing import Any, Dict, Optional, Union
from ..models.config import StorageBackendConfig
from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage

# Import all storage implementations
from .memory import (
    AsyncMemoryQueue, MemoryQueue,
    AsyncMemoryResultStorage, MemoryResultStorage,
    AsyncMemoryEventStorage, MemoryEventStorage,
    AsyncMemoryScheduleStorage, MemoryScheduleStorage,
)
from .sqlite import (
    AsyncSQLiteQueue, SQLiteQueue,
    AsyncSQLiteResultStorage, SQLiteResultStorage,
    AsyncSQLiteEventStorage, SQLiteEventStorage,
    AsyncSQLiteScheduleStorage, SQLiteScheduleStorage,
)
from .file import (
    AsyncFileQueue, FileQueue,
    AsyncFileResultStorage, FileResultStorage,
    AsyncFileEventStorage, FileEventStorage,
    AsyncFileScheduleStorage, FileScheduleStorage,
)
# Note: Some imports may not exist yet, but we'll include them for completeness
# The factory will gracefully handle missing implementations

try:
    from .redis import (
        AsyncRedisQueue, RedisQueue,
        AsyncRedisResultStorage, RedisResultStorage,
        AsyncRedisEventStorage, RedisEventStorage,
    )
    # Schedule storage may not exist yet
    try:
        from .redis import AsyncRedisScheduleStorage, RedisScheduleStorage
    except ImportError:
        AsyncRedisScheduleStorage = None
        RedisScheduleStorage = None
except ImportError:
    AsyncRedisQueue = RedisQueue = None
    AsyncRedisResultStorage = RedisResultStorage = None
    AsyncRedisEventStorage = RedisEventStorage = None
    AsyncRedisScheduleStorage = RedisScheduleStorage = None

try:
    from .postgres import (
        AsyncPostgresQueue, PostgresQueue,
        AsyncPostgresResultStorage, PostgresResultStorage,
        AsyncPostgresEventStorage, PostgresEventStorage,
    )
    try:
        from .postgres import AsyncPostgresScheduleStorage, PostgresScheduleStorage
    except ImportError:
        AsyncPostgresScheduleStorage = None
        PostgresScheduleStorage = None
except ImportError:
    AsyncPostgresQueue = PostgresQueue = None
    AsyncPostgresResultStorage = PostgresResultStorage = None
    AsyncPostgresEventStorage = PostgresEventStorage = None
    AsyncPostgresScheduleStorage = PostgresScheduleStorage = None

try:
    from .nats import (
        AsyncNATSQueue, NATSQueue,
        AsyncNATSResultStorage, NATSResultStorage,
        AsyncNATSEventStorage, NATSEventStorage,
    )
    try:
        from .nats import AsyncNATSScheduleStorage, NATSScheduleStorage
    except ImportError:
        AsyncNATSScheduleStorage = None
        NATSScheduleStorage = None
except ImportError:
    AsyncNATSQueue = NATSQueue = None
    AsyncNATSResultStorage = NATSResultStorage = None
    AsyncNATSEventStorage = NATSEventStorage = None
    AsyncNATSScheduleStorage = NATSScheduleStorage = None

try:
    from .azure import (
        AsyncAzureQueue, AzureQueue,
        AsyncAzureResultStorage, AzureResultStorage,
        AsyncAzureEventStorage, AzureEventStorage,
    )
    try:
        from .azure import AsyncAzureScheduleStorage, AzureScheduleStorage
    except ImportError:
        AsyncAzureScheduleStorage = None
        AzureScheduleStorage = None
except ImportError:
    AsyncAzureQueue = AzureQueue = None
    AsyncAzureResultStorage = AzureResultStorage = None
    AsyncAzureEventStorage = AzureEventStorage = None
    AsyncAzureScheduleStorage = AzureScheduleStorage = None

try:
    from .gcs import (
        AsyncGCSQueue, GCSQueue,
        AsyncGCSResultStorage, GCSResultStorage,
        AsyncGCSEventStorage, GCSEventStorage,
    )
    try:
        from .gcs import AsyncGCSScheduleStorage, GCSScheduleStorage
    except ImportError:
        AsyncGCSScheduleStorage = None
        GCSScheduleStorage = None
except ImportError:
    AsyncGCSQueue = GCSQueue = None
    AsyncGCSResultStorage = GCSResultStorage = None
    AsyncGCSEventStorage = GCSEventStorage = None
    AsyncGCSScheduleStorage = GCSScheduleStorage = None

try:
    from .s3 import (
        AsyncS3Queue, S3Queue,
        AsyncS3ResultStorage, S3ResultStorage,
        AsyncS3EventStorage, S3EventStorage,
    )
    try:
        from .s3 import AsyncS3ScheduleStorage, S3ScheduleStorage
    except ImportError:
        AsyncS3ScheduleStorage = None
        S3ScheduleStorage = None
except ImportError:
    AsyncS3Queue = S3Queue = None
    AsyncS3ResultStorage = S3ResultStorage = None
    AsyncS3EventStorage = S3EventStorage = None
    AsyncS3ScheduleStorage = S3ScheduleStorage = None


class StorageBackendFactory:
    """Factory for creating individual storage components."""
    
    @classmethod
    def _build_registry(cls, storage_classes):
        """Build registry filtering out None values."""
        registry = {}
        for backend, classes in storage_classes.items():
            if classes["async"] is not None or classes["sync"] is not None:
                registry[backend] = {
                    k: v for k, v in classes.items() if v is not None
                }
        return registry
    
    # Registry of available storage implementations
    @classmethod
    def _get_task_queue_registry(cls):
        return cls._build_registry({
            "memory": {"async": AsyncMemoryQueue, "sync": MemoryQueue},
            "sqlite": {"async": AsyncSQLiteQueue, "sync": SQLiteQueue},
            "file": {"async": AsyncFileQueue, "sync": FileQueue},
            "redis": {"async": AsyncRedisQueue, "sync": RedisQueue},
            "postgres": {"async": AsyncPostgresQueue, "sync": PostgresQueue},
            "nats": {"async": AsyncNATSQueue, "sync": NATSQueue},
            "azure": {"async": AsyncAzureQueue, "sync": AzureQueue},
            "gcs": {"async": AsyncGCSQueue, "sync": GCSQueue},
            "s3": {"async": AsyncS3Queue, "sync": S3Queue},
        })
    
    @classmethod
    def _get_result_storage_registry(cls):
        return cls._build_registry({
            "memory": {"async": AsyncMemoryResultStorage, "sync": MemoryResultStorage},
            "sqlite": {"async": AsyncSQLiteResultStorage, "sync": SQLiteResultStorage},
            "file": {"async": AsyncFileResultStorage, "sync": FileResultStorage},
            "redis": {"async": AsyncRedisResultStorage, "sync": RedisResultStorage},
            "postgres": {"async": AsyncPostgresResultStorage, "sync": PostgresResultStorage},
            "nats": {"async": AsyncNATSResultStorage, "sync": NATSResultStorage},
            "azure": {"async": AsyncAzureResultStorage, "sync": AzureResultStorage},
            "gcs": {"async": AsyncGCSResultStorage, "sync": GCSResultStorage},
            "s3": {"async": AsyncS3ResultStorage, "sync": S3ResultStorage},
        })
    
    @classmethod
    def _get_event_storage_registry(cls):
        return cls._build_registry({
            "memory": {"async": AsyncMemoryEventStorage, "sync": MemoryEventStorage},
            "sqlite": {"async": AsyncSQLiteEventStorage, "sync": SQLiteEventStorage},
            "file": {"async": AsyncFileEventStorage, "sync": FileEventStorage},
            "redis": {"async": AsyncRedisEventStorage, "sync": RedisEventStorage},
            "postgres": {"async": AsyncPostgresEventStorage, "sync": PostgresEventStorage},
            "nats": {"async": AsyncNATSEventStorage, "sync": NATSEventStorage},
            "azure": {"async": AsyncAzureEventStorage, "sync": AzureEventStorage},
            "gcs": {"async": AsyncGCSEventStorage, "sync": GCSEventStorage},
            "s3": {"async": AsyncS3EventStorage, "sync": S3EventStorage},
        })
    
    @classmethod
    def _get_schedule_storage_registry(cls):
        return cls._build_registry({
            "memory": {"async": AsyncMemoryScheduleStorage, "sync": MemoryScheduleStorage},
            "sqlite": {"async": AsyncSQLiteScheduleStorage, "sync": SQLiteScheduleStorage},
            "file": {"async": AsyncFileScheduleStorage, "sync": FileScheduleStorage},
            "redis": {"async": AsyncRedisScheduleStorage, "sync": RedisScheduleStorage},
            "postgres": {"async": AsyncPostgresScheduleStorage, "sync": PostgresScheduleStorage},
            "nats": {"async": AsyncNATSScheduleStorage, "sync": NATSScheduleStorage},
            "azure": {"async": AsyncAzureScheduleStorage, "sync": AzureScheduleStorage},
            "gcs": {"async": AsyncGCSScheduleStorage, "sync": GCSScheduleStorage},
            "s3": {"async": AsyncS3ScheduleStorage, "sync": S3ScheduleStorage},
        })
    
    @classmethod
    def create_task_queue(
        cls,
        config: StorageBackendConfig,
        async_mode: bool = True
    ) -> BaseTaskQueue:
        """
        Create a task queue instance based on configuration.
        
        Args:
            config: Storage backend configuration
            async_mode: Whether to create async or sync version
            
        Returns:
            Task queue instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        backend_type = config.backend_type.lower()
        mode = "async" if async_mode else "sync"
        
        task_queue_registry = cls._get_task_queue_registry()
        
        if backend_type not in task_queue_registry:
            raise ValueError(f"Unsupported task queue backend: {backend_type}")
        
        if mode not in task_queue_registry[backend_type]:
            raise ValueError(f"Mode '{mode}' not supported for backend '{backend_type}'")
        
        storage_class = task_queue_registry[backend_type][mode]
        
        # Create instance with configuration
        return cls._create_storage_instance(storage_class, config)
    
    @classmethod
    def create_result_storage(
        cls,
        config: StorageBackendConfig,
        async_mode: bool = True
    ) -> BaseResultStorage:
        """
        Create a result storage instance based on configuration.
        
        Args:
            config: Storage backend configuration
            async_mode: Whether to create async or sync version
            
        Returns:
            Result storage instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        backend_type = config.backend_type.lower()
        mode = "async" if async_mode else "sync"
        
        result_storage_registry = cls._get_result_storage_registry()
        
        if backend_type not in result_storage_registry:
            raise ValueError(f"Unsupported result storage backend: {backend_type}")
        
        if mode not in result_storage_registry[backend_type]:
            raise ValueError(f"Mode '{mode}' not supported for backend '{backend_type}'")
        
        storage_class = result_storage_registry[backend_type][mode]
        
        # Create instance with configuration
        return cls._create_storage_instance(storage_class, config)
    
    @classmethod
    def create_event_storage(
        cls,
        config: StorageBackendConfig,
        async_mode: bool = True
    ) -> BaseEventStorage:
        """
        Create an event storage instance based on configuration.
        
        Args:
            config: Storage backend configuration
            async_mode: Whether to create async or sync version
            
        Returns:
            Event storage instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        backend_type = config.backend_type.lower()
        mode = "async" if async_mode else "sync"
        
        event_storage_registry = cls._get_event_storage_registry()
        
        if backend_type not in event_storage_registry:
            raise ValueError(f"Unsupported event storage backend: {backend_type}")
        
        if mode not in event_storage_registry[backend_type]:
            raise ValueError(f"Mode '{mode}' not supported for backend '{backend_type}'")
        
        storage_class = event_storage_registry[backend_type][mode]
        
        # Create instance with configuration
        return cls._create_storage_instance(storage_class, config)
    
    @classmethod
    def create_schedule_storage(
        cls,
        config: StorageBackendConfig,
        async_mode: bool = True
    ) -> BaseScheduleStorage:
        """
        Create a schedule storage instance based on configuration.
        
        Args:
            config: Storage backend configuration
            async_mode: Whether to create async or sync version
            
        Returns:
            Schedule storage instance
            
        Raises:
            ValueError: If backend type is not supported
        """
        backend_type = config.backend_type.lower()
        mode = "async" if async_mode else "sync"
        
        schedule_storage_registry = cls._get_schedule_storage_registry()
        
        if backend_type not in schedule_storage_registry:
            raise ValueError(f"Unsupported schedule storage backend: {backend_type}")
        
        if mode not in schedule_storage_registry[backend_type]:
            raise ValueError(f"Mode '{mode}' not supported for backend '{backend_type}'")
        
        storage_class = schedule_storage_registry[backend_type][mode]
        
        # Create instance with configuration
        return cls._create_storage_instance(storage_class, config)
    
    @classmethod
    def _create_storage_instance(cls, storage_class, config: StorageBackendConfig):
        """
        Create a storage instance with the appropriate configuration.
        
        Args:
            storage_class: The storage class to instantiate
            config: Storage backend configuration
            
        Returns:
            Storage instance
        """
        # Prepare initialization arguments
        init_args = {}
        
        # Handle URL-based configuration
        if config.url:
            init_args = cls._parse_url_config(config.url, config.backend_type)
        
        # Handle dictionary-based configuration
        if config.config:
            init_args.update(config.config)
        
        # Create instance
        try:
            return storage_class(**init_args)
        except Exception as e:
            raise ValueError(f"Failed to create {storage_class.__name__} instance: {e}")
    
    @classmethod
    def _parse_url_config(cls, url: str, backend_type: str) -> Dict[str, Any]:
        """
        Parse URL configuration into initialization arguments.
        
        Args:
            url: Connection URL
            backend_type: Backend type
            
        Returns:
            Dictionary of initialization arguments
        """
        if backend_type == "sqlite":
            if url.startswith("sqlite:///"):
                return {"database_path": url[10:]}
            elif url.startswith("sqlite://"):
                return {"database_path": url[9:]}
            else:
                return {"database_path": url}
        
        elif backend_type == "redis":
            # Parse Redis URL (redis://host:port/db)
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            config = {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 6379,
            }
            if parsed.path and parsed.path != "/":
                config["database"] = int(parsed.path[1:])
            if parsed.password:
                config["password"] = parsed.password
            return config
        
        elif backend_type == "postgres":
            # Parse PostgreSQL URL (postgresql://user:pass@host:port/db)
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            config = {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path[1:] if parsed.path else "omniq",
            }
            if parsed.username:
                config["username"] = parsed.username
            if parsed.password:
                config["password"] = parsed.password
            return config
        
        elif backend_type == "file":
            # Parse file URL (file:///path or just path)
            if url.startswith("file://"):
                return {"base_dir": url[7:]}
            else:
                return {"base_dir": url}
        
        elif backend_type in ["azure", "gcs", "s3"]:
            # For cloud storage, URL might be the bucket/container name
            return {"bucket_name": url} if backend_type in ["gcs", "s3"] else {"container_name": url}
        
        elif backend_type == "nats":
            # Parse NATS URL (nats://host:port)
            return {"servers": [url]}
        
        else:
            # For other backends, return URL as-is
            return {"url": url}
    
    @classmethod
    def get_supported_backends(cls) -> Dict[str, list]:
        """
        Get list of supported backends for each storage type.
        
        Returns:
            Dictionary mapping storage types to supported backends
        """
        return {
            "task_queue": list(cls._get_task_queue_registry().keys()),
            "result_storage": list(cls._get_result_storage_registry().keys()),
            "event_storage": list(cls._get_event_storage_registry().keys()),
            "schedule_storage": list(cls._get_schedule_storage_registry().keys()),
        }


# Convenience functions for creating storage components
def create_task_queue(
    backend_type: str,
    async_mode: bool = True,
    url: Optional[str] = None,
    **config
) -> BaseTaskQueue:
    """
    Create a task queue instance.
    
    Args:
        backend_type: Backend type (sqlite, redis, etc.)
        async_mode: Whether to create async or sync version
        url: Connection URL (optional)
        **config: Additional configuration options
        
    Returns:
        Task queue instance
    """
    backend_config = StorageBackendConfig(
        backend_type=backend_type,
        url=url,
        config=config if config else None
    )
    return StorageBackendFactory.create_task_queue(backend_config, async_mode)


def create_result_storage(
    backend_type: str,
    async_mode: bool = True,
    url: Optional[str] = None,
    **config
) -> BaseResultStorage:
    """
    Create a result storage instance.
    
    Args:
        backend_type: Backend type (sqlite, redis, etc.)
        async_mode: Whether to create async or sync version
        url: Connection URL (optional)
        **config: Additional configuration options
        
    Returns:
        Result storage instance
    """
    backend_config = StorageBackendConfig(
        backend_type=backend_type,
        url=url,
        config=config if config else None
    )
    return StorageBackendFactory.create_result_storage(backend_config, async_mode)


def create_event_storage(
    backend_type: str,
    async_mode: bool = True,
    url: Optional[str] = None,
    **config
) -> BaseEventStorage:
    """
    Create an event storage instance.
    
    Args:
        backend_type: Backend type (sqlite, redis, etc.)
        async_mode: Whether to create async or sync version
        url: Connection URL (optional)
        **config: Additional configuration options
        
    Returns:
        Event storage instance
    """
    backend_config = StorageBackendConfig(
        backend_type=backend_type,
        url=url,
        config=config if config else None
    )
    return StorageBackendFactory.create_event_storage(backend_config, async_mode)


def create_schedule_storage(
    backend_type: str,
    async_mode: bool = True,
    url: Optional[str] = None,
    **config
) -> BaseScheduleStorage:
    """
    Create a schedule storage instance.
    
    Args:
        backend_type: Backend type (sqlite, redis, etc.)
        async_mode: Whether to create async or sync version
        url: Connection URL (optional)
        **config: Additional configuration options
        
    Returns:
        Schedule storage instance
    """
    backend_config = StorageBackendConfig(
        backend_type=backend_type,
        url=url,
        config=config if config else None
    )
    return StorageBackendFactory.create_schedule_storage(backend_config, async_mode)