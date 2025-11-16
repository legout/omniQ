"""Storage abstractions for OmniQ tasks and results."""

from __future__ import annotations

from .base import BaseStorage, Serializer, TaskError

__all__ = ["BaseStorage", "Serializer", "TaskError"]
