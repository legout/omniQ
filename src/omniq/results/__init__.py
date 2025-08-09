"""Result storage components for OmniQ.

This package provides result storage interfaces and implementations for:
- Result storage

Available implementations:
- SQLite-based result storage (sqlite module)
"""

from .base import BaseResultStorage
from .sqlite import AsyncSQLiteResultStorage, SQLiteResultStorage

__all__ = [
    # Base interface
    "BaseResultStorage",
    # SQLite implementations
    "AsyncSQLiteResultStorage",
    "SQLiteResultStorage",
]