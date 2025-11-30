"""
OmniQ - Async-first task queue library.

Provides simple, reliable task execution with support for:
- Async and sync APIs
- Multiple storage backends (file, SQLite)
- Configurable serialization (msgspec, cloudpickle)
- Retry logic and scheduling
- Worker pools
"""

from .core import AsyncOmniQ, OmniQ
from .config import Settings, BackendType
from .models import Task, TaskResult, TaskStatus
from .storage import BaseStorage

# Public API exports
__all__ = [
    "AsyncOmniQ",
    "OmniQ",
    "Settings",
    "BackendType",
    "Task",
    "TaskResult",
    "TaskStatus",
    "BaseStorage",
]

# Version info
__version__ = "0.1.0"
