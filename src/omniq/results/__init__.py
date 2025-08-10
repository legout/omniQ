"""Result storage components for OmniQ.

This package provides result storage interfaces and implementations for:
- Result storage

Available implementations:
- SQLite-based result storage (sqlite module)
"""

from .base import BaseResultStorage
from .sqlite import AsyncSQLiteResultStorage, SQLiteResultStorage
from .file import AsyncFileResultStorage, FileResultStorage
from .memory import AsyncMemoryResultStorage, MemoryResultStorage
from .redis import AsyncRedisResultStorage, RedisResultStorage
from .nats import (
    AsyncNATSResultStorage,
    NATSResultStorage,
    AsyncNatsResultStorage,
    NatsResultStorage,
)
from .postgres import AsyncPostgresResultStorage, PostgresResultStorage


__all__ = [
    # Base interface
    "BaseResultStorage",
    # SQLite implementations
    "AsyncSQLiteResultStorage",
    "SQLiteResultStorage",
    # File-based result storage
    "AsyncFileResultStorage",
    "FileResultStorage",
    # Memory-based result storage
    "AsyncMemoryResultStorage",
    "MemoryResultStorage",
    # Redis-based result storage
    "AsyncRedisResultStorage",
    "RedisResultStorage",
    # NATS-based result storage
    "AsyncNATSResultStorage",
    "NATSResultStorage",
    # Alias for NATS result storage
    "AsyncNatsResultStorage",
    "NatsResultStorage",
    # Postgres-based result storage
    "AsyncPostgresResultStorage",
    "PostgresResultStorage",
]
