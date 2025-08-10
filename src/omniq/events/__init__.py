"""Event storage components for OmniQ.

This package provides event storage interfaces and implementations for:
- Event logging and retrieval

Available implementations:
- SQLite-based event storage (sqlite module)
"""

from .base import BaseEventStorage
from .sqlite import AsyncSQLiteEventStorage, SQLiteEventStorage
from .file import AsyncFileEventStorage, FileEventStorage

# from .nats import AsyncNATSEventStorage, NATSEventStorage
# from .redis import AsyncRedisEventStorage, RedisEventStorage
from .postgres import AsyncPostgresEventStorage, PostgresEventStorage

__all__ = [
    # Base interface
    "BaseEventStorage",
    # SQLite implementations
    "AsyncSQLiteEventStorage",
    "SQLiteEventStorage",
    # File-based event storage
    "AsyncFileEventStorage",
    "FileEventStorage",
    # NATS-based event storage
    # "AsyncNATSEventStorage",
    # "NATSEventStorage",
    # Redis-based event storage
    # "AsyncRedisEventStorage",
    # "RedisEventStorage",
    # Postgres-based event storage
    "AsyncPostgresEventStorage",
    "PostgresEventStorage",
]
