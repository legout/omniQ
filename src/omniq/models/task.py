from __future__ import annotations
import time
from typing import Any, Callable, Coroutine
import msgspec

class Task(msgspec.Struct, kw_only=True):
    """
    Represents a task to be executed.
    """
    # Core task information
    func: Callable[..., Any] | Coroutine[Any, Any, Any]
    func_args: dict[str, Any] = {}

    # Task metadata
    id: str
    name: str | None = None
    
    # Execution control
    ttl: int | None = None  # Time-to-live in seconds
    timeout: int | None = None # Task execution timeout in seconds
    
    # Scheduling
    scheduled_at: float | None = None # Timestamp to schedule the task
    
    # Dependencies
    dependencies: list[str] = [] # List of task IDs this task depends on
    
    # Callbacks
    on_success: Callable[[Any], None] | None = None
    on_failure: Callable[[Exception], None] | None = None
    
    # Result handling
    result_ttl: int | None = None # Time-to-live for the result in seconds
    
    # Internal tracking
    created_at: float = msgspec.field(default_factory=time.time)
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.func.__name__

