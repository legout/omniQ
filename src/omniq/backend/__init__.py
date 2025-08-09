"""Backend implementations for OmniQ.

This package provides backend interfaces and implementations that act as
factories for creating storage component instances.

Available backends:
- SQLite backend (sqlite module)
"""

from .base import BaseBackend
from .sqlite import SQLiteBackend

__all__ = [
    "BaseBackend",
    "SQLiteBackend",
]