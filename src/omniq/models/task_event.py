from typing import Any, Dict
from msgspec import Struct, field
from datetime import datetime
import uuid

class TaskEvent(Struct):
    """
    Represents an event in the task lifecycle for logging and monitoring.
    Supports structured logging with metadata for efficient querying.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = field() # type: ignore
    event_type: str = field()  # type: ignore # e.g., ENQUEUED, EXECUTING, COMPLETE, ERROR, RETRY, CANCELLED, EXPIRED
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional event-specific data

    def __str__(self) -> str:
        """String representation of the event for logging purposes."""
        return f"TaskEvent({self.event_type}, Task ID: {self.task_id}, Timestamp: {self.timestamp})"
