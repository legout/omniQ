# src/omniq/models/config.py
"""Configuration classes for OmniQ."""

from typing import List, Dict, Any, Optional
import msgspec

# Base config classes
class TaskQueueConfig(msgspec.Struct):
    """Base configuration for task queues."""
    type: str
    config: Dict[str, Any]

class ResultStoreConfig(msgspec.Struct):
    """Base configuration for result storage."""
    type: str
    config: Dict[str, Any]

class EventStoreConfig(msgspec.Struct):
    """Base configuration for event storage."""
    type: str
    config: Dict[str, Any]

class WorkerConfig(msgspec.Struct):
    """Base configuration for workers."""
    type: str
    config: Dict[str, Any]

class OmniQConfig(msgspec.Struct):
    """Main configuration for OmniQ."""
    project_name: str
    task_queue: TaskQueueConfig
    result_store: Optional[ResultStoreConfig] = None
    event_store: Optional[EventStoreConfig] = None
    worker: Optional[WorkerConfig] = None

# --- Backend base config classes ---

class FileConfig(msgspec.Struct):
    project_name: str
    base_dir: str
    protocol: str = "file"
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)

class MemoryConfig(msgspec.Struct):
    project_name: str

class SQLiteConfig(msgspec.Struct):
    project_name: str
    base_dir: str

class PostgresConfig(msgspec.Struct):
    project_name: str
    host: str
    username: str
    password: str
    port: int = 5432
    database: str = "omniq"

class RedisConfig(msgspec.Struct):
    project_name: str
    host: str
    port: int = 6379
    password: Optional[str] = None
    database: int = 0

class NATSConfig(msgspec.Struct):
    project_name: str
    servers: List[str]

# --- Specific task queue configs ---

class FileTaskQueueConfig(FileConfig):
    """Configuration for file task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

class MemoryTaskQueueConfig(MemoryConfig):
    """Configuration for memory task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

class SQLiteTaskQueueConfig(SQLiteConfig):
    """Configuration for SQLite task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

class PostgresTaskQueueConfig(PostgresConfig):
    """Configuration for PostgreSQL task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

class RedisTaskQueueConfig(RedisConfig):
    """Configuration for Redis task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

class NATSTaskQueueConfig(NATSConfig):
    """Configuration for NATS task queue."""
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])

# --- Specific result storage configs ---

class FileResultStorageConfig(FileConfig):
    """Configuration for file result storage."""

class MemoryResultStorageConfig(MemoryConfig):
    """Configuration for memory result storage."""

class SQLiteResultStorageConfig(SQLiteConfig):
    """Configuration for SQLite result storage."""

class PostgresResultStorageConfig(PostgresConfig):
    """Configuration for PostgreSQL result storage."""

class RedisResultStorageConfig(RedisConfig):
    """Configuration for Redis result storage."""

class NATSResultStorageConfig(NATSConfig):
    """Configuration for NATS result storage."""

# --- Specific event storage configs ---

class FileEventStorageConfig(FileConfig):
    """Configuration for file event storage."""

class SQLiteEventStorageConfig(SQLiteConfig):
    """Configuration for SQLite event storage."""

class PostgresEventStorageConfig(PostgresConfig):
    """Configuration for PostgreSQL event storage."""

# --- Specific worker configs ---

class AsyncWorkerConfig(msgspec.Struct):
    """Configuration for async worker."""
    max_workers: int = 10

class ThreadPoolWorkerConfig(msgspec.Struct):
    """Configuration for thread pool worker."""
    max_workers: int = 10

class ProcessPoolWorkerConfig(msgspec.Struct):
    """Configuration for process pool worker."""
    max_workers: int = 4

class GeventPoolWorkerConfig(msgspec.Struct):
    """Configuration for gevent pool worker."""
    max_workers: int = 100