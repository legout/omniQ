"""
OmniQ Data Models

This module contains the core data structures used throughout the OmniQ task queue library.
All models use msgspec.Struct for high-performance serialization and validation.
"""

import enum
import hashlib
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

import msgspec
from croniter import croniter


class TaskStatus(enum.Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(enum.Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class EventType(enum.Enum):
    """Task event type enumeration."""
    ENQUEUED = "enqueued"
    DEQUEUED = "dequeued"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ERROR = "error"
    RETRY = "retry"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Task(msgspec.Struct):
    """
    Task data structure representing a unit of work to be executed.
    
    Attributes:
        func: Callable function to execute (can be async or sync)
        id: Unique task identifier
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        queue: Queue name for the task
        priority: Task priority level
        status: Current execution status
        created_at: Task creation timestamp
        scheduled_at: When the task should be executed
        ttl: Time-to-live in seconds (for automatic expiration)
        max_retries: Maximum number of retry attempts
        retry_count: Current retry attempt count
        retry_delay: Delay between retries in seconds
        dependencies: Set of task IDs this task depends on
        dependents: Set of task IDs that depend on this task
        metadata: Additional task metadata
        result_ttl: Time-to-live for task results in seconds
        callback: Optional callback function to execute after completion
        error_callback: Optional callback function to execute on error
    """
    
    # Core task identification and function (required fields first)
    func: Callable = msgspec.field()
    
    # Optional fields with defaults
    id: UUID = msgspec.field(default_factory=uuid4)
    args: tuple = msgspec.field(default_factory=tuple)
    kwargs: dict = msgspec.field(default_factory=dict)
    
    # Queue and execution metadata
    queue: str = msgspec.field(default="default")
    priority: TaskPriority = msgspec.field(default=TaskPriority.NORMAL)
    status: TaskStatus = msgspec.field(default=TaskStatus.PENDING)
    
    # Timing and scheduling
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = msgspec.field(default=None)
    ttl: Optional[int] = msgspec.field(default=None)  # Time-to-live in seconds
    
    # Retry configuration
    max_retries: int = msgspec.field(default=3)
    retry_count: int = msgspec.field(default=0)
    retry_delay: float = msgspec.field(default=1.0)
    
    # Dependencies and relationships
    dependencies: Set[UUID] = msgspec.field(default_factory=set)
    dependents: Set[UUID] = msgspec.field(default_factory=set)
    
    # Additional metadata and callbacks
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    result_ttl: Optional[int] = msgspec.field(default=None)
    callback: Optional[Callable] = msgspec.field(default=None)
    error_callback: Optional[Callable] = msgspec.field(default=None)
    
    def __hash__(self) -> int:
        """Hash based on task ID for dependency tracking."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Equality based on task ID."""
        if not isinstance(other, Task):
            return False
        return self.id == other.id
    
    def is_expired(self) -> bool:
        """Check if the task has expired based on TTL."""
        if self.ttl is None:
            return False
        expiry_time = self.created_at + timedelta(seconds=self.ttl)
        return datetime.utcnow() > expiry_time
    
    def is_ready_for_execution(self) -> bool:
        """Check if task is ready for execution (dependencies met, scheduled time passed)."""
        if self.status != TaskStatus.QUEUED:
            return False
        
        # Check if scheduled time has passed
        if self.scheduled_at and datetime.utcnow() < self.scheduled_at:
            return False
        
        # Check if expired
        if self.is_expired():
            return False
        
        return True
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries
    
    def get_next_retry_time(self) -> datetime:
        """Calculate the next retry time with exponential backoff."""
        delay = self.retry_delay * (2 ** self.retry_count)
        return datetime.utcnow() + timedelta(seconds=delay)


class Schedule(msgspec.Struct):
    """
    Schedule data structure for recurring tasks.
    
    Attributes:
        id: Unique schedule identifier
        task_template: Task template to use for scheduled executions
        cron_expression: Cron expression for scheduling
        timezone: Timezone for schedule evaluation
        is_active: Whether the schedule is currently active
        start_time: When the schedule becomes active
        end_time: When the schedule expires
        max_executions: Maximum number of executions (None for unlimited)
        execution_count: Current number of executions
        last_execution: Timestamp of last execution
        next_execution: Timestamp of next scheduled execution
        paused: Whether the schedule is temporarily paused
        paused_at: When the schedule was paused
        metadata: Additional schedule metadata
    """
    
    # Required fields first
    task_template: Task
    cron_expression: str
    
    # Optional fields with defaults
    id: UUID = msgspec.field(default_factory=uuid4)
    timezone: str = msgspec.field(default="UTC")
    
    # Schedule lifecycle
    is_active: bool = msgspec.field(default=True)
    start_time: Optional[datetime] = msgspec.field(default=None)
    end_time: Optional[datetime] = msgspec.field(default=None)
    
    # Execution tracking
    max_executions: Optional[int] = msgspec.field(default=None)
    execution_count: int = msgspec.field(default=0)
    last_execution: Optional[datetime] = msgspec.field(default=None)
    next_execution: Optional[datetime] = msgspec.field(default=None)
    
    # Pause/resume functionality
    paused: bool = msgspec.field(default=False)
    paused_at: Optional[datetime] = msgspec.field(default=None)
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __hash__(self) -> int:
        """Hash based on schedule ID for dependency tracking."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Equality based on schedule ID."""
        if not isinstance(other, Schedule):
            return False
        return self.id == other.id
    
    def __post_init__(self):
        """Initialize next execution time if not set."""
        if self.next_execution is None:
            self.calculate_next_execution()
    
    def calculate_next_execution(self) -> None:
        """Calculate the next execution time based on cron expression."""
        if not self.is_active or self.paused:
            return
        
        try:
            cron = croniter(self.cron_expression, datetime.utcnow())
            next_time = cron.get_next(datetime)
            
            # Check if within active time window
            if self.start_time and next_time < self.start_time:
                next_time = self.start_time
            
            if self.end_time and next_time > self.end_time:
                self.is_active = False
                return
            
            self.next_execution = next_time
        except Exception:
            # Invalid cron expression, deactivate schedule
            self.is_active = False
    
    def is_due(self) -> bool:
        """Check if the schedule is due for execution."""
        if not self.is_active or self.paused or not self.next_execution:
            return False
        
        # Check execution limits
        if self.max_executions and self.execution_count >= self.max_executions:
            self.is_active = False
            return False
        
        return datetime.utcnow() >= self.next_execution
    
    def pause(self) -> None:
        """Pause the schedule."""
        self.paused = True
        self.paused_at = datetime.utcnow()
    
    def resume(self) -> None:
        """Resume the schedule."""
        self.paused = False
        self.paused_at = None
        self.calculate_next_execution()
    
    def create_task(self) -> Task:
        """Create a new task instance from the template."""
        # Create a new task with a new ID but same function and parameters
        task = Task(
            func=self.task_template.func,
            args=self.task_template.args,
            kwargs=self.task_template.kwargs,
            queue=self.task_template.queue,
            priority=self.task_template.priority,
            max_retries=self.task_template.max_retries,
            retry_delay=self.task_template.retry_delay,
            ttl=self.task_template.ttl,
            result_ttl=self.task_template.result_ttl,
            callback=self.task_template.callback,
            error_callback=self.task_template.error_callback,
            metadata={**self.task_template.metadata, "schedule_id": str(self.id)}
        )
        
        # Update execution tracking
        self.execution_count += 1
        self.last_execution = datetime.utcnow()
        self.calculate_next_execution()
        
        return task


class TaskResult(msgspec.Struct):
    """
    Task result data structure for storing execution outcomes.
    
    Attributes:
        task_id: ID of the task this result belongs to
        status: Final execution status
        result: Actual result value (if successful)
        error: Error information (if failed)
        started_at: When execution started
        completed_at: When execution completed
        execution_time: Total execution time in seconds
        worker_id: ID of the worker that executed the task
        retry_count: Number of retries before completion
        metadata: Additional result metadata
        ttl: Time-to-live for the result in seconds
    """
    
    # Core result identification (required fields)
    task_id: UUID
    status: TaskStatus
    
    # Result data
    result: Any = msgspec.field(default=None)
    error: Optional[str] = msgspec.field(default=None)
    
    # Timing information
    started_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = msgspec.field(default=None)
    execution_time: Optional[float] = msgspec.field(default=None)
    
    # Execution context
    worker_id: Optional[str] = msgspec.field(default=None)
    retry_count: int = msgspec.field(default=0)
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    ttl: Optional[int] = msgspec.field(default=None)
    
    def __hash__(self) -> int:
        """Hash based on task ID."""
        return hash(self.task_id)
    
    def __eq__(self, other) -> bool:
        """Equality based on task ID."""
        if not isinstance(other, TaskResult):
            return False
        return self.task_id == other.task_id
    
    def is_expired(self) -> bool:
        """Check if the result has expired based on TTL."""
        if self.ttl is None or self.completed_at is None:
            return False
        expiry_time = self.completed_at + timedelta(seconds=self.ttl)
        return datetime.utcnow() > expiry_time
    
    def is_success(self) -> bool:
        """Check if the task execution was successful."""
        return self.status == TaskStatus.COMPLETE
    
    def is_failure(self) -> bool:
        """Check if the task execution failed."""
        return self.status == TaskStatus.FAILED
    
    def complete(self, result: Any = None) -> None:
        """Mark the result as complete with optional result value."""
        self.status = TaskStatus.COMPLETE
        self.result = result
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def fail(self, error: str) -> None:
        """Mark the result as failed with error information."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()


class TaskEvent(msgspec.Struct):
    """
    Task event data structure for lifecycle logging.
    
    Attributes:
        id: Unique event identifier
        task_id: ID of the task this event belongs to
        event_type: Type of event
        timestamp: When the event occurred
        message: Human-readable event message
        data: Additional event data
        worker_id: ID of the worker that generated the event
        queue: Queue name where the event occurred
        metadata: Additional event metadata
    """
    
    # Required fields first
    task_id: UUID
    event_type: EventType
    
    # Optional fields with defaults
    id: UUID = msgspec.field(default_factory=uuid4)
    timestamp: datetime = msgspec.field(default_factory=datetime.utcnow)
    message: str = msgspec.field(default="")
    data: Dict[str, Any] = msgspec.field(default_factory=dict)
    worker_id: Optional[str] = msgspec.field(default=None)
    queue: str = msgspec.field(default="default")
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __hash__(self) -> int:
        """Hash based on event ID."""
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """Equality based on event ID."""
        if not isinstance(other, TaskEvent):
            return False
        return self.id == other.id
    
    @classmethod
    def create_enqueued(cls, task_id: UUID, queue: str = "default", **kwargs) -> "TaskEvent":
        """Create an ENQUEUED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.ENQUEUED,
            message=f"Task enqueued in queue '{queue}'",
            queue=queue,
            **kwargs
        )
    
    @classmethod
    def create_dequeued(cls, task_id: UUID, worker_id: str, queue: str = "default", **kwargs) -> "TaskEvent":
        """Create a DEQUEUED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.DEQUEUED,
            message=f"Task dequeued by worker '{worker_id}' from queue '{queue}'",
            worker_id=worker_id,
            queue=queue,
            **kwargs
        )
    
    @classmethod
    def create_executing(cls, task_id: UUID, worker_id: str, **kwargs) -> "TaskEvent":
        """Create an EXECUTING event."""
        return cls(
            task_id=task_id,
            event_type=EventType.EXECUTING,
            message=f"Task execution started by worker '{worker_id}'",
            worker_id=worker_id,
            **kwargs
        )
    
    @classmethod
    def create_complete(cls, task_id: UUID, worker_id: str, execution_time: float, **kwargs) -> "TaskEvent":
        """Create a COMPLETE event."""
        return cls(
            task_id=task_id,
            event_type=EventType.COMPLETE,
            message=f"Task completed successfully by worker '{worker_id}' in {execution_time:.2f}s",
            worker_id=worker_id,
            data={"execution_time": execution_time},
            **kwargs
        )
    
    @classmethod
    def create_error(cls, task_id: UUID, worker_id: str, error: str, **kwargs) -> "TaskEvent":
        """Create an ERROR event."""
        return cls(
            task_id=task_id,
            event_type=EventType.ERROR,
            message=f"Task failed with error: {error}",
            worker_id=worker_id,
            data={"error": error},
            **kwargs
        )
    
    @classmethod
    def create_retry(cls, task_id: UUID, retry_count: int, next_retry_time: datetime, **kwargs) -> "TaskEvent":
        """Create a RETRY event."""
        return cls(
            task_id=task_id,
            event_type=EventType.RETRY,
            message=f"Task scheduled for retry #{retry_count} at {next_retry_time}",
            data={"retry_count": retry_count, "next_retry_time": next_retry_time.isoformat()},
            **kwargs
        )
    
    @classmethod
    def create_cancelled(cls, task_id: UUID, reason: str = "User requested", **kwargs) -> "TaskEvent":
        """Create a CANCELLED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.CANCELLED,
            message=f"Task cancelled: {reason}",
            data={"reason": reason},
            **kwargs
        )
    
    @classmethod
    def create_expired(cls, task_id: UUID, ttl: int, **kwargs) -> "TaskEvent":
        """Create an EXPIRED event."""
        return cls(
            task_id=task_id,
            event_type=EventType.EXPIRED,
            message=f"Task expired after {ttl} seconds",
            data={"ttl": ttl},
            **kwargs
        )