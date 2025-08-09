"""Event storage components for OmniQ.

This package provides event storage interfaces and implementations for:
- Event logging and retrieval

Available implementations:
- SQLite-based event storage (sqlite module)
"""

from .base import BaseEventStorage
from .sqlite import AsyncSQLiteEventStorage, SQLiteEventStorage

__all__ = [
    # Base interface
    "BaseEventStorage",
    # SQLite implementations
    "AsyncSQLiteEventStorage",
    "SQLiteEventStorage",
]