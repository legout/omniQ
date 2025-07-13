"""Task model with metadata, dependencies, and TTL."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

import msgspec


class TaskDependency(msgspec.Struct):
    """Task dependency specification."""
    
    task_id: str
    required: bool = True


class TaskCallback(msgspec.Struct):
    """Task callback specification."""
    
    name: str
    on_success: bool = True
    on_failure: bool = True
    on_retry: bool = False
    args: Optional[List[Any]] = None
    kwargs: Optional[Dict[str, Any]] = None


class Task(msgspec.Struct):
    """Core task model with comprehensive metadata and lifecycle management."""
    
    # Required fields first
    name: str
    func: Union[str, Callable]  # Function name/path or callable
    
    # Optional fields with defaults
    id: str = msgspec.field(default_factory=lambda: str(uuid4()))
    args: List[Any] = msgspec.field(default_factory=list)
    kwargs: Dict[str, Any] = msgspec.field(default_factory=dict)
    queue: str = "default"
    priority: int = 0  # Higher values = higher priority
    created_at: float = msgspec.field(default_factory=time.time)
    scheduled_at: Optional[float] = None  # When to execute (Unix timestamp)
    ttl: Optional[int] = None  # Time-to-live in seconds
    timeout: Optional[int] = None  # Execution timeout in seconds
    dependencies: List[TaskDependency] = msgspec.field(default_factory=list)
    callbacks: List[TaskCallback] = msgspec.field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds
    retry_backoff: str = "exponential"  # "linear", "exponential", "fixed"
    retry_jitter: bool = True
    tags: Dict[str, str] = msgspec.field(default_factory=dict)
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    worker_type: Optional[str] = None  # "async", "thread", "process", "gevent"
    environment: Dict[str, str] = msgspec.field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if task has exceeded its TTL."""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)
    
    def is_ready(self) -> bool:
        """Check if task is ready for execution (not scheduled in future)."""
        if self.scheduled_at is None:
            return True
        return time.time() >= self.scheduled_at
    
    def get_effective_priority(self) -> tuple:
        """Get priority tuple for sorting (higher priority first, then FIFO)."""
        return (-self.priority, self.created_at)
    
    def add_dependency(self, task_id: str, required: bool = True) -> None:
        """Add a task dependency."""
        self.dependencies.append(TaskDependency(task_id=task_id, required=required))
    
    def add_callback(
        self,
        name: str,
        on_success: bool = True,
        on_failure: bool = True,
        on_retry: bool = False,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a task callback."""
        self.callbacks.append(TaskCallback(
            name=name,
            on_success=on_success,
            on_failure=on_failure,
            on_retry=on_retry,
            args=args or [],
            kwargs=kwargs or {}
        ))
    
    def with_tags(self, **tags: str) -> Task:
        """Return new task with additional tags."""
        new_tags = {**self.tags, **tags}
        return msgspec.structs.replace(self, tags=new_tags)
    
    def with_metadata(self, **metadata: Any) -> Task:
        """Return new task with additional metadata."""
        new_metadata = {**self.metadata, **metadata}
        return msgspec.structs.replace(self, metadata=new_metadata)