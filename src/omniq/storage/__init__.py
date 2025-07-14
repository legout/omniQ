"""
OmniQ Storage Module

This module provides storage interfaces and implementations for the OmniQ task queue library.
It includes abstract base classes for task queues, result storage, and event storage.
"""

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

__all__ = ["BaseTaskQueue", "BaseResultStorage", "BaseEventStorage"]