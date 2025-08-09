"""Configuration models for OmniQ components.

This module defines msgspec.Struct-based configuration objects that provide
type validation for component configurations.
"""

from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import msgspec


class BaseConfig(msgspec.Struct):
    """Base configuration class with common fields."""
    project_name: str = "omniq"
    base_dir: str = "./omniq_data"


class SQLiteQueueConfig(BaseConfig):
    """Configuration for SQLite-based task queue."""
    db_path: Optional[str] = None
    table_name: str = "tasks"
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    connection_timeout: int = 30
    max_connections: int = 10


class FileQueueConfig(BaseConfig):
    """Configuration for file-based task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    fsspec_uri: str = "file://"
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)


class MemoryQueueConfig(BaseConfig):
    """Configuration for memory-based task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    max_size: Optional[int] = None


class PostgresQueueConfig(BaseConfig):
    """Configuration for PostgreSQL-based task queue."""
    host: str = "localhost"
    port: int = 5432
    database: str = "omniq"
    username: str = "postgres"
    password: Optional[str] = None
    table_name: str = "tasks"
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    connection_timeout: int = 30
    max_connections: int = 10
    ssl_mode: str = "prefer"


class RedisQueueConfig(BaseConfig):
    """Configuration for Redis-based task queue."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    queue_prefix: str = "omniq:queue"
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    connection_timeout: int = 30
    max_connections: int = 10


class NATSQueueConfig(BaseConfig):
    """Configuration for NATS-based task queue."""
    servers: List[str] = msgspec.field(default_factory=lambda: ["nats://localhost:4222"])
    subject_prefix: str = "omniq.queue"
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    connection_timeout: int = 30
    max_reconnect_attempts: int = 10


class SQLiteResultStorageConfig(BaseConfig):
    """Configuration for SQLite-based result storage."""
    db_path: Optional[str] = None
    table_name: str = "results"
    connection_timeout: int = 30
    max_connections: int = 10


class FileResultStorageConfig(BaseConfig):
    """Configuration for file-based result storage."""
    fsspec_uri: str = "file://"
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)
    results_dir: str = "results"


class MemoryResultStorageConfig(BaseConfig):
    """Configuration for memory-based result storage."""
    max_size: Optional[int] = None


class PostgresResultStorageConfig(BaseConfig):
    """Configuration for PostgreSQL-based result storage."""
    host: str = "localhost"
    port: int = 5432
    database: str = "omniq"
    username: str = "postgres"
    password: Optional[str] = None
    table_name: str = "results"
    connection_timeout: int = 30
    max_connections: int = 10
    ssl_mode: str = "prefer"


class RedisResultStorageConfig(BaseConfig):
    """Configuration for Redis-based result storage."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    key_prefix: str = "omniq:result"
    connection_timeout: int = 30
    max_connections: int = 10


class NATSResultStorageConfig(BaseConfig):
    """Configuration for NATS-based result storage."""
    servers: List[str] = msgspec.field(default_factory=lambda: ["nats://localhost:4222"])
    subject_prefix: str = "omniq.result"
    connection_timeout: int = 30
    max_reconnect_attempts: int = 10


class SQLiteEventStorageConfig(BaseConfig):
    """Configuration for SQLite-based event storage."""
    db_path: Optional[str] = None
    table_name: str = "events"
    connection_timeout: int = 30
    max_connections: int = 10


class FileEventStorageConfig(BaseConfig):
    """Configuration for file-based event storage."""
    fsspec_uri: str = "file://"
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)
    events_dir: str = "events"


class PostgresEventStorageConfig(BaseConfig):
    """Configuration for PostgreSQL-based event storage."""
    host: str = "localhost"
    port: int = 5432
    database: str = "omniq"
    username: str = "postgres"
    password: Optional[str] = None
    table_name: str = "events"
    connection_timeout: int = 30
    max_connections: int = 10
    ssl_mode: str = "prefer"


class AsyncWorkerConfig(msgspec.Struct):
    """Configuration for async worker."""
    max_workers: int = 4
    task_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0


class ThreadWorkerConfig(msgspec.Struct):
    """Configuration for thread pool worker."""
    max_workers: int = 4
    task_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0


class ProcessWorkerConfig(msgspec.Struct):
    """Configuration for process pool worker."""
    max_workers: int = 2
    task_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0


class GeventWorkerConfig(msgspec.Struct):
    """Configuration for gevent worker."""
    max_workers: int = 100
    task_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0


class OmniQConfig(msgspec.Struct):
    """Main OmniQ configuration."""
    project_name: str = "omniq"
    
    # Task queue configuration
    task_queue_type: str = "file"
    task_queue_config: Optional[Dict[str, Any]] = None
    
    # Result storage configuration
    result_storage_type: str = "file"
    result_storage_config: Optional[Dict[str, Any]] = None
    
    # Event storage configuration
    event_storage_type: Optional[str] = "sqlite"
    event_storage_config: Optional[Dict[str, Any]] = None
    
    # Worker configuration
    worker_type: str = "async"
    worker_config: Optional[Dict[str, Any]] = None
    
    # Global settings
    task_ttl: int = 3600  # 1 hour
    result_ttl: int = 86400  # 24 hours
    log_level: str = "INFO"
    disable_logging: bool = False


# Type aliases for configuration unions
QueueConfig = Union[
    SQLiteQueueConfig,
    FileQueueConfig,
    MemoryQueueConfig,
    PostgresQueueConfig,
    RedisQueueConfig,
    NATSQueueConfig
]

ResultStorageConfig = Union[
    SQLiteResultStorageConfig,
    FileResultStorageConfig,
    MemoryResultStorageConfig,
    PostgresResultStorageConfig,
    RedisResultStorageConfig,
    NATSResultStorageConfig
]

EventStorageConfig = Union[
    SQLiteEventStorageConfig,
    FileEventStorageConfig,
    PostgresEventStorageConfig
]

WorkerConfig = Union[
    AsyncWorkerConfig,
    ThreadWorkerConfig,
    ProcessWorkerConfig,
    GeventWorkerConfig
]