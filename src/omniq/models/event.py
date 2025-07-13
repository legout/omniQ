"""TaskEvent model for lifecycle logging."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, Optional

import msgspec


class TaskEventType(str, Enum):
    """Task lifecycle event types."""
    
    # Task lifecycle
    ENQUEUED = "enqueued"
    DEQUEUED = "dequeued"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    
    # Retry events
    RETRY_SCHEDULED = "retry_scheduled"
    RETRY_STARTED = "retry_started"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    
    # Dependency events
    DEPENDENCY_SATISFIED = "dependency_satisfied"
    DEPENDENCY_FAILED = "dependency_failed"
    WAITING_FOR_DEPENDENCIES = "waiting_for_dependencies"
    
    # Schedule events
    SCHEDULED = "scheduled"
    SCHEDULE_TRIGGERED = "schedule_triggered"
    SCHEDULE_PAUSED = "schedule_paused"
    SCHEDULE_RESUMED = "schedule_resumed"
    SCHEDULE_DEACTIVATED = "schedule_deactivated"
    
    # Worker events
    WORKER_ASSIGNED = "worker_assigned"
    WORKER_RELEASED = "worker_released"
    
    # Queue events
    QUEUE_PRIORITY_CHANGED = "queue_priority_changed"
    QUEUE_MOVED = "queue_moved"
    
    # TTL events
    TTL_EXPIRED = "ttl_expired"
    TTL_EXTENDED = "ttl_extended"


class TaskEvent(msgspec.Struct):
    """Task lifecycle event for comprehensive logging and monitoring."""
    
    # Core identification
    task_id: str
    event_type: TaskEventType
    timestamp: float = msgspec.field(default_factory=time.time)
    
    # Context information
    worker_id: Optional[str] = None
    worker_type: Optional[str] = None
    queue_name: Optional[str] = None
    
    # Event-specific data
    message: Optional[str] = None
    details: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Error information (for failure events)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    
    # Metadata
    tags: Dict[str, str] = msgspec.field(default_factory=dict)
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    @classmethod
    def enqueued(
        cls,
        task_id: str,
        queue_name: str,
        priority: int = 0,
        **kwargs
    ) -> TaskEvent:
        """Create task enqueued event."""
        return cls(
            task_id=task_id,
            event_type=TaskEventType.ENQUEUED,
            queue_name=queue_name,
            message=f"Task enqueued to '{queue_name}' with priority {priority}",
            details={"priority": priority},
            **kwargs
        )
    
    @classmethod
    def started(
        cls,
        task_id: str,
        worker_id: str,
        worker_type: str,
        **kwargs
    ) -> TaskEvent:
        """Create task started event."""
        return cls(
            task_id=task_id,
            event_type=TaskEventType.STARTED,
            worker_id=worker_id,
            worker_type=worker_type,
            message=f"Task started on {worker_type} worker {worker_id}",
            **kwargs
        )
    
    @classmethod
    def completed(
        cls,
        task_id: str,
        worker_id: str,
        duration_ms: float,
        **kwargs
    ) -> TaskEvent:
        """Create task completed event."""
        return cls(
            task_id=task_id,
            event_type=TaskEventType.COMPLETED,
            worker_id=worker_id,
            duration_ms=duration_ms,
            message=f"Task completed successfully in {duration_ms:.2f}ms",
            **kwargs
        )
    
    @classmethod
    def failed(
        cls,
        task_id: str,
        worker_id: str,
        error: Exception,
        duration_ms: float,
        retry_count: int = 0,
        **kwargs
    ) -> TaskEvent:
        """Create task failed event."""
        return cls(
            task_id=task_id,
            event_type=TaskEventType.FAILED,
            worker_id=worker_id,
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error),
            message=f"Task failed after {duration_ms:.2f}ms (retry {retry_count})",
            details={"retry_count": retry_count},
            **kwargs
        )
    
    @classmethod
    def retry_scheduled(
        cls,
        task_id: str,
        retry_count: int,
        retry_delay: float,
        **kwargs
    ) -> TaskEvent:
        """Create retry scheduled event."""
        return cls(
            task_id=task_id,
            event_type=TaskEventType.RETRY_SCHEDULED,
            message=f"Retry {retry_count} scheduled in {retry_delay}s",
            details={"retry_count": retry_count, "retry_delay": retry_delay},
            **kwargs
        )
    
    @classmethod
    def dependency_event(
        cls,
        task_id: str,
        event_type: TaskEventType,
        dependency_task_id: str,
        **kwargs
    ) -> TaskEvent:
        """Create dependency-related event."""
        return cls(
            task_id=task_id,
            event_type=event_type,
            message=f"Dependency {dependency_task_id} {event_type.value}",
            details={"dependency_task_id": dependency_task_id},
            **kwargs
        )
    
    @classmethod
    def schedule_event(
        cls,
        task_id: str,
        event_type: TaskEventType,
        schedule_name: str,
        next_run: Optional[float] = None,
        **kwargs
    ) -> TaskEvent:
        """Create schedule-related event."""
        details = {"schedule_name": schedule_name}
        if next_run is not None:
            details["next_run"] = next_run
        
        return cls(
            task_id=task_id,
            event_type=event_type,
            message=f"Schedule '{schedule_name}' {event_type.value}",
            details=details,
            **kwargs
        )
    
    def is_error_event(self) -> bool:
        """Check if event represents an error condition."""
        return self.event_type in (
            TaskEventType.FAILED,
            TaskEventType.TIMEOUT,
            TaskEventType.CANCELLED,
            TaskEventType.MAX_RETRIES_EXCEEDED,
            TaskEventType.DEPENDENCY_FAILED,
            TaskEventType.TTL_EXPIRED
        )
    
    def is_completion_event(self) -> bool:
        """Check if event represents task completion."""
        return self.event_type in (
            TaskEventType.COMPLETED,
            TaskEventType.FAILED,
            TaskEventType.TIMEOUT,
            TaskEventType.CANCELLED
        )
    
    def with_tags(self, **tags: str) -> TaskEvent:
        """Return new event with additional tags."""
        new_tags = {**self.tags, **tags}
        return msgspec.structs.replace(self, tags=new_tags)
    
    def with_metadata(self, **metadata: Any) -> TaskEvent:
        """Return new event with additional metadata."""
        new_metadata = {**self.metadata, **metadata}
        return msgspec.structs.replace(self, metadata=new_metadata)