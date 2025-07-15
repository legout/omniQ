"""
Task event model for OmniQ.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

import msgspec
from msgspec import Struct


class EventType(str, Enum):
    """Task event types."""
    ENQUEUED = "enqueued"
    DEQUEUED = "dequeued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SCHEDULE_PAUSED = "schedule_paused"
    SCHEDULE_RESUMED = "schedule_resumed"


class TaskEvent(Struct):
    """
    Represents a task lifecycle event in OmniQ.
    
    This class is used for logging and monitoring task execution
    throughout its lifecycle, providing rich metadata for debugging
    and analysis.
    """
    
    # Required fields first
    task_id: str
    event_type: EventType
    
    # Core identification
    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    
    # Timing
    timestamp: datetime = msgspec.field(default_factory=datetime.utcnow)
    
    # Event details
    message: Optional[str] = None
    details: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Context information
    worker_id: Optional[str] = None
    queue_name: Optional[str] = None
    schedule_id: Optional[str] = None
    
    # Error information (for failed events)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    
    # Performance metrics
    execution_time: Optional[float] = None  # in seconds
    memory_usage: Optional[int] = None  # in bytes
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return msgspec.to_builtins(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskEvent":
        """Create event from dictionary representation."""
        return msgspec.convert(data, cls)
    
    @classmethod
    def create_enqueued(
        cls,
        task_id: str,
        queue_name: str,
        schedule_id: Optional[str] = None,
        **kwargs
    ) -> "TaskEvent":
        """Create an ENQUEUED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.ENQUEUED,
            queue_name=queue_name,
            schedule_id=schedule_id,
            message=f"Task enqueued to queue '{queue_name}'",
            **kwargs
        )
    
    @classmethod
    def create_dequeued(
        cls,
        task_id: str,
        queue_name: str,
        worker_id: str,
        **kwargs
    ) -> "TaskEvent":
        """Create a DEQUEUED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.DEQUEUED,
            queue_name=queue_name,
            worker_id=worker_id,
            message=f"Task dequeued from queue '{queue_name}' by worker '{worker_id}'",
            **kwargs
        )
    
    @classmethod
    def create_executing(
        cls,
        task_id: str,
        worker_id: str,
        **kwargs
    ) -> "TaskEvent":
        """Create an EXECUTING event."""
        return cls(
            task_id=task_id,
            event_type=EventType.EXECUTING,
            worker_id=worker_id,
            message=f"Task execution started by worker '{worker_id}'",
            **kwargs
        )
    
    @classmethod
    def create_completed(
        cls,
        task_id: str,
        worker_id: str,
        execution_time: Optional[float] = None,
        **kwargs
    ) -> "TaskEvent":
        """Create a COMPLETED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.COMPLETED,
            worker_id=worker_id,
            execution_time=execution_time,
            message=f"Task completed successfully by worker '{worker_id}'",
            **kwargs
        )
    
    @classmethod
    def create_failed(
        cls,
        task_id: str,
        worker_id: str,
        error: Exception,
        traceback_str: Optional[str] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ) -> "TaskEvent":
        """Create a FAILED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.FAILED,
            worker_id=worker_id,
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback_str,
            execution_time=execution_time,
            message=f"Task failed in worker '{worker_id}': {error}",
            **kwargs
        )
    
    @classmethod
    def create_retry(
        cls,
        task_id: str,
        retry_count: int,
        max_retries: int,
        **kwargs
    ) -> "TaskEvent":
        """Create a RETRY event."""
        return cls(
            task_id=task_id,
            event_type=EventType.RETRY,
            message=f"Task retry {retry_count}/{max_retries}",
            details={"retry_count": retry_count, "max_retries": max_retries},
            **kwargs
        )
    
    @classmethod
    def create_cancelled(
        cls,
        task_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> "TaskEvent":
        """Create a CANCELLED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.CANCELLED,
            message=f"Task cancelled{f': {reason}' if reason else ''}",
            **kwargs
        )
    
    @classmethod
    def create_expired(
        cls,
        task_id: str,
        **kwargs
    ) -> "TaskEvent":
        """Create an EXPIRED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.EXPIRED,
            message="Task expired due to TTL",
            **kwargs
        )
    
    @classmethod
    def create_schedule_paused(
        cls,
        task_id: str,
        schedule_id: str,
        **kwargs
    ) -> "TaskEvent":
        """Create a SCHEDULE_PAUSED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.SCHEDULE_PAUSED,
            schedule_id=schedule_id,
            message=f"Schedule '{schedule_id}' paused",
            **kwargs
        )
    
    @classmethod
    def create_schedule_resumed(
        cls,
        task_id: str,
        schedule_id: str,
        **kwargs
    ) -> "TaskEvent":
        """Create a SCHEDULE_RESUMED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.SCHEDULE_RESUMED,
            schedule_id=schedule_id,
            message=f"Schedule '{schedule_id}' resumed",
            **kwargs
        )