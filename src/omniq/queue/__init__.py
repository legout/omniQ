"""Queue components for OmniQ.

This package provides queue interfaces and implementations for task queuing.

Available implementations:
- SQLite-based queue (sqlite module)
- Scheduler for recurring tasks (scheduler module)
- Dependency resolver for task dependencies (dependency module)
"""

from .base import BaseQueue
from .sqlite import AsyncSQLiteQueue, SQLiteQueue
from .file import AsyncFileQueue, FileQueue
from .memory import AsyncMemoryQueue, MemoryQueue
from .redis import AsyncRedisQueue, RedisQueue
from .nats import AsyncNATSQueue, NATSQueue, AsyncNatsQueue, NatsQueue
from .postgres import AsyncPostgresQueue, PostgresQueue
from .scheduler import AsyncScheduler, Scheduler
from .dependency import DependencyResolver
from .retry import RetryManager

__all__ = [
    # Base interface
    "BaseQueue",
    # SQLite implementations
    "AsyncSQLiteQueue",
    "SQLiteQueue",
    # Scheduler implementations
    "AsyncScheduler",
    "Scheduler",
    # Dependency management
    "DependencyResolver",
    # Retry management
    "RetryManager",
    # File-based queue
    "AsyncFileQueue",
    "FileQueue",
    # Memory-based queue
    "AsyncMemoryQueue",
    "MemoryQueue",
    # Redis-based queue
    "AsyncRedisQueue",
    "RedisQueue",
    # NATS-based queue
    "AsyncNATSQueue",
    "NATSQueue",
    # Alias for NATS queue
    "AsyncNatsQueue",
    "NatsQueue",
    # Postgres-based queue
    "AsyncPostgresQueue",
    "PostgresQueue",
]
