# src/omniq/models/event.py
"""Event model for OmniQ."""

from typing import Dict, Any, Optional
from datetime import datetime
import msgspec
import enum

class EventType(enum.Enum):
    """Enumeration for event types."""
    ENQUEUED = "ENQUEUED"
    EXECUTING = "EXECUTING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SCHEDULE_PAUSED = "SCHEDULE_PAUSED"
    SCHEDULE_RESUMED = "SCHEDULE_RESUMED"


class TaskEvent(msgspec.Struct):
    """Task event model for OmniQ."""
    
    task_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        task_id: str,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None
    ) -> "TaskEvent":
        """Create a new task event."""
        return cls(
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.now(),
            data=data or {}
        )