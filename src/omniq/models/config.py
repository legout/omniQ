"""Configuration models using msgspec.Struct."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import msgspec


class QueueConfig(msgspec.Struct):
    """Task queue configuration."""
    
    # Queue identification
    name: str = "default"
    
    # Backend configuration
    backend_type: str = "memory"  # "memory", "file", "sqlite", "postgres", "redis", "nats"
    connection_string: Optional[str] = None
    
    # Queue behavior
    max_size: Optional[int] = None
    priority_enabled: bool = True
    fifo_within_priority: bool = True
    
    # TTL and cleanup
    default_task_ttl: Optional[int] = None  # seconds
    cleanup_interval: int = 300  # seconds
    
    # Persistence (for file/memory backends)
    persist_to_disk: bool = False
    persistence_path: Optional[str] = None
    
    # Connection pooling
    max_connections: int = 10
    connection_timeout: float = 30.0


class WorkerConfig(msgspec.Struct):
    """Worker configuration."""
    
    # Worker identification
    worker_type: str = "async"  # "async", "thread", "process", "gevent"
    worker_id: Optional[str] = None
    
    # Pool configuration
    pool_size: int = 4
    max_pool_size: Optional[int] = None
    
    # Task execution
    task_timeout: Optional[int] = None  # seconds
    heartbeat_interval: float = 30.0  # seconds
    
    # Queue processing
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    queue_priorities: Dict[str, int] = msgspec.field(default_factory=dict)
    polling_interval: float = 1.0  # seconds
    batch_size: int = 1
    
    # Graceful shutdown
    shutdown_timeout: float = 30.0  # seconds
    
    # Process-specific (for ProcessWorker)
    process_initializer: Optional[str] = None
    process_initargs: List[Any] = msgspec.field(default_factory=list)


class StorageConfig(msgspec.Struct):
    """Storage backend configuration."""
    
    # Backend type and connection
    backend_type: str = "memory"
    connection_string: Optional[str] = None
    
    # Database configuration (for SQL backends)
    database_name: Optional[str] = None
    table_prefix: str = "omniq"
    schema_name: Optional[str] = None
    
    # Connection pooling
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    
    # File storage configuration
    base_path: Optional[str] = None
    compression: bool = False
    
    # Cloud storage configuration
    cloud_provider: Optional[str] = None  # "s3", "azure", "gcp"
    bucket_name: Optional[str] = None
    region: Optional[str] = None
    
    # TTL and cleanup
    default_ttl: Optional[int] = None  # seconds
    cleanup_enabled: bool = True
    cleanup_interval: int = 3600  # seconds
    
    # Serialization
    serialization_format: str = "msgspec"  # "msgspec", "json", "pickle"
    compression_level: int = 6


class SerializationConfig(msgspec.Struct):
    """Serialization configuration."""
    
    # Primary serialization strategy
    primary_serializer: str = "msgspec"  # "msgspec", "json", "pickle", "dill"
    fallback_serializer: str = "dill"
    
    # Msgspec configuration
    msgspec_strict: bool = True
    msgspec_dec_hook: Optional[str] = None
    msgspec_enc_hook: Optional[str] = None
    
    # Compression
    compress: bool = False
    compression_algorithm: str = "gzip"  # "gzip", "bz2", "lzma"
    compression_level: int = 6
    
    # Type detection
    auto_detect_types: bool = True
    type_registry: Dict[str, str] = msgspec.field(default_factory=dict)


class EventConfig(msgspec.Struct):
    """Event logging configuration."""
    
    # Event storage
    enabled: bool = True
    storage_backend: str = "memory"  # "memory", "file", "sqlite", "postgres"
    connection_string: Optional[str] = None
    
    # Event filtering
    event_types: List[str] = msgspec.field(default_factory=list)  # Empty = all events
    min_level: str = "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR"
    
    # Batching and performance
    batch_size: int = 100
    flush_interval: float = 5.0  # seconds
    max_buffer_size: int = 10000
    
    # TTL and cleanup
    event_ttl: Optional[int] = None  # seconds
    cleanup_interval: int = 3600  # seconds
    
    # Async processing
    async_processing: bool = True
    queue_size: int = 1000


class OmniQConfig(msgspec.Struct):
    """Main OmniQ configuration combining all component configurations."""
    
    # Component configurations
    queue: QueueConfig = msgspec.field(default_factory=QueueConfig)
    worker: WorkerConfig = msgspec.field(default_factory=WorkerConfig)
    storage: StorageConfig = msgspec.field(default_factory=StorageConfig)
    serialization: SerializationConfig = msgspec.field(default_factory=SerializationConfig)
    events: EventConfig = msgspec.field(default_factory=EventConfig)
    
    # Global settings
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Component independence
    task_storage: Optional[StorageConfig] = None
    result_storage: Optional[StorageConfig] = None
    event_storage: Optional[StorageConfig] = None
    
    # Default timeouts and limits
    default_task_timeout: Optional[int] = None  # seconds
    default_result_ttl: int = 86400  # 24 hours
    default_event_ttl: int = 604800  # 7 days
    
    # Monitoring and health checks
    health_check_enabled: bool = True
    health_check_interval: float = 60.0  # seconds
    metrics_enabled: bool = False
    
    def get_task_storage_config(self) -> StorageConfig:
        """Get task storage configuration (with fallback to main storage)."""
        return self.task_storage or self.storage
    
    def get_result_storage_config(self) -> StorageConfig:
        """Get result storage configuration (with fallback to main storage)."""
        return self.result_storage or self.storage
    
    def get_event_storage_config(self) -> StorageConfig:
        """Get event storage configuration (with fallback to main storage)."""
        return self.event_storage or self.storage
    
    def with_debug(self, enabled: bool = True) -> OmniQConfig:
        """Return configuration with debug mode enabled/disabled."""
        log_level = "DEBUG" if enabled else "INFO"
        return msgspec.structs.replace(
            self,
            debug=enabled,
            log_level=log_level
        )