"""Worker implementations for OmniQ.

This module provides various worker implementations for executing tasks:
- BaseWorker: Abstract base class for all workers
- AsyncWorker: Core async worker implementation
- ThreadPoolWorker: Synchronous wrapper around AsyncWorker
"""

from .base import BaseWorker
from .thread import ThreadPoolWorker

__all__ = [
    "BaseWorker",
    "ThreadPoolWorker",
]