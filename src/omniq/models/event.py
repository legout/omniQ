from __future__ import annotations
import time
from typing import Any
import msgspec

class TaskEvent(msgspec.Struct, kw_only=True):
    """
    Represents a lifecycle event of a task.
    """
    # Event details
    event_id: str
    task_id: str
    event_type: str # e.g., ENQUEUED, EXECUTING, COMPLETED, FAILED
    
    # Associated data
    data: dict[str, Any] = {}
    
    # Timestamp
    timestamp: float = msgspec.field(default_factory=time.time)
