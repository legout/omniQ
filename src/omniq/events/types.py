"""Event types for OmniQ task lifecycle tracking."""

from enum import Enum

class EventType(Enum):
    """Enumeration of event types for task lifecycle events."""
    ENQUEUED = "enqueued"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ERROR = "error"
    RETRY = "retry"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SCHEDULE_PAUSED = "schedule_paused"
    SCHEDULE_RESUMED = "schedule_resumed"
