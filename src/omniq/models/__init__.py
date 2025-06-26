import time
import uuid
from typing import Any, Dict, List, Optional

import msgspec


class Task(msgspec.Struct, kw_only=True, gc=False):
    """Represents a task to be executed."""

    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    func: Any  # Will be a serialized callable (e.g., via dill)
    args: tuple[Any, ...] = ()
    kwargs: Dict[str, Any] = {}
    queue: str = "default"  # The queue this task belongs to
    created_at: float = msgspec.field(default_factory=time.time)
    ttl: Optional[int] = None  # Time-to-live in seconds
    dependencies: List[str] = []  # List of task IDs this task depends on
    retries: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds
    # New fields for dependency tracking
    status: str = "pending"  # e.g., pending, waiting, processing, failed
    dependencies_left: int = 0


class Schedule(msgspec.Struct, kw_only=True, gc=False):
    """Represents a scheduled task."""

    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    task: Task
    cron: Optional[str] = None
    interval: Optional[float] = None  # Interval in seconds
    is_paused: bool = False
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None


class TaskResult(msgspec.Struct, kw_only=True, gc=False):
    """Represents the result of a task execution."""

    task_id: str
    status: str  # e.g., 'SUCCESS', 'FAILURE'
    result: Any
    started_at: float
    completed_at: float = msgspec.field(default_factory=time.time)
    worker_id: Optional[str] = None
    ttl: Optional[int] = None  # Time-to-live in seconds


class TaskEvent(msgspec.Struct, kw_only=True, gc=False):
    """Represents a lifecycle event of a task."""

    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    event_type: str  # e.g., 'ENQUEUED', 'EXECUTING', 'COMPLETED', 'FAILED'
    timestamp: float = msgspec.field(default_factory=time.time)
    details: Dict[str, Any] = {}