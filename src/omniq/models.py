from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional, Dict

from typing_extensions import NotRequired, TypedDict


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ErrorType(str, Enum):
    """Standard error types for categorization."""

    RUNTIME = "runtime"  # Runtime errors during execution
    TIMEOUT = "timeout"  # Task timeout errors
    VALIDATION = "validation"  # Input validation errors
    RESOURCE = "resource"  # Resource exhaustion errors
    NETWORK = "network"  # Network-related errors
    SYSTEM = "system"  # System-level errors
    USER = "user"  # User-defined errors
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class TaskError:
    """Structured error information for failed tasks.

    Simplified v1 model with 6 core fields.
    """

    # Core error information
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    traceback: Optional[str] = None

    # Retry information
    retry_count: int = 0
    is_retryable: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize error data."""
        # Normalize error_type to lowercase
        self.error_type = self.error_type.lower()

    def can_retry(self) -> bool:
        """Check if error is retryable based on configuration."""
        return self.is_retryable

    def increment_retry(self) -> "TaskError":
        """Create a new TaskError with incremented retry count."""
        return TaskError(
            error_type=self.error_type,
            message=self.message,
            timestamp=self.timestamp,
            traceback=self.traceback,
            retry_count=self.retry_count + 1,
            is_retryable=self.is_retryable,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
            "retry_count": self.retry_count,
            "is_retryable": self.is_retryable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskError":
        """Create TaskError from dictionary with backward compatibility."""
        # Handle timestamp conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            error_type=data.get("error_type", "unknown"),
            message=data.get("message", ""),
            timestamp=timestamp,
            traceback=data.get("traceback"),
            retry_count=data.get("retry_count", 0),
            is_retryable=data.get("is_retryable", True),
        )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        message: Optional[str] = None,
        error_type: str = "runtime",
        is_retryable: bool = True,
    ) -> "TaskError":
        """Create TaskError from exception."""
        import traceback

        return cls(
            error_type=error_type,
            message=message or str(exception),
            timestamp=datetime.now(timezone.utc),
            traceback=traceback.format_exc(),
            is_retryable=is_retryable,
        )


class Schedule(TypedDict):
    """Scheduling configuration for task execution.

    Controls when and how frequently a task should be executed. Used in
    conjunction with the Task model to define delayed or recurring tasks.

    Attributes:
        eta: Estimated time of arrival - the datetime when the task should
            first execute. If None, the task is eligible for immediate execution.
        interval: Time interval between executions for recurring tasks. If set,
            the task will be rescheduled after each successful completion.
            Can be None for one-time tasks.

    Example:
        >>> from datetime import datetime, timedelta
        >>>
        >>> # Task scheduled for specific time
        >>> schedule1: Schedule = {"eta": datetime(2025, 1, 1, 12, 0)}
        >>>
        >>> # Task that runs every hour
        >>> schedule2: Schedule = {"interval": timedelta(hours=1)}
        >>>
        >>> # Task with both eta and interval (starts at eta, then repeats)
        >>> schedule3: Schedule = {
        ...     "eta": datetime(2025, 1, 1, 12, 0),
        ...     "interval": timedelta(hours=1)
        ... }
    """

    eta: NotRequired[Optional[datetime]]
    interval: NotRequired[Optional[timedelta]]  # time interval


class Task(TypedDict):
    """Core task model representing a unit of work in the queue.

    A Task encapsulates all information needed to execute, track, and retry
    a function call asynchronously. Tasks transition through status states
    (PENDING -> RUNNING -> SUCCESS/FAILED) with automatic retry support.

    Attributes:
        id: Unique identifier for the task (UUID string).
        func_path: Dot-separated import path to the function to execute
            (e.g., "my_module.process_data").
        args: Positional arguments to pass to the function.
        kwargs: Keyword arguments to pass to the function.
        status: Current task status (PENDING, RUNNING, SUCCESS, FAILED,
            or CANCELLED).
        schedule: Scheduling configuration for delayed or recurring tasks.
        max_retries: Maximum number of retry attempts after failure.
        timeout: Maximum execution time in seconds. If None, no timeout
            is enforced.
        attempts: Number of times the task has been attempted.
        created_at: Timestamp when the task was created (UTC).
        updated_at: Timestamp of the last task update (UTC).
        last_attempt_at: Timestamp when the task last started execution (UTC).
        error: Structured error information if the task failed.

    Example:
        >>> from datetime import datetime, timedelta
        >>>
        >>> task: Task = {
        ...     "id": "abc123",
        ...     "func_path": "myapp.tasks.process_image",
        ...     "args": ["image.png"],
        ...     "kwargs": {"quality": 90},
        ...     "status": TaskStatus.PENDING,
        ...     "schedule": {},
        ...     "max_retries": 3,
        ...     "timeout": 300,
        ...     "attempts": 0,
        ...     "created_at": datetime.now(timezone.utc),
        ...     "updated_at": datetime.now(timezone.utc),
        ...     "last_attempt_at": None,
        ... }
    """

    id: str
    func_path: str
    args: list[Any]
    kwargs: dict[str, Any]
    status: TaskStatus
    schedule: Schedule
    max_retries: int
    timeout: Optional[int]  # seconds
    attempts: int
    created_at: datetime
    updated_at: datetime
    last_attempt_at: Optional[datetime]
    error: NotRequired[Optional[TaskError]]  # Structured error information


class TaskResult(TypedDict):
    """Result returned after task execution completes or fails.

    Provides the outcome of task execution, including either the successful
    result or error information. Used by public APIs to return task results
    to callers.

    Attributes:
        task_id: ID of the task that produced this result.
        status: Final task status (SUCCESS or FAILED).
        result: The return value from the task function if successful. None
            if the task failed.
        error: Error message string if the task failed. None if successful.
        finished_at: Timestamp when the task finished execution (UTC).
        attempts: Total number of execution attempts made.
        last_attempt_at: Timestamp when the last execution attempt started (UTC).

    Example:
        >>> from datetime import datetime, timezone
        >>>
        >>> # Successful result
        >>> success: TaskResult = {
        ...     "task_id": "abc123",
        ...     "status": TaskStatus.SUCCESS,
        ...     "result": 42,
        ...     "error": None,
        ...     "finished_at": datetime.now(timezone.utc),
        ...     "attempts": 1,
        ...     "last_attempt_at": datetime.now(timezone.utc),
        ... }
        >>>
        >>> # Failed result
        >>> failure: TaskResult = {
        ...     "task_id": "abc123",
        ...     "status": TaskStatus.FAILED,
        ...     "result": None,
        ...     "error": "Division by zero",
        ...     "finished_at": datetime.now(timezone.utc),
        ...     "attempts": 3,
        ...     "last_attempt_at": datetime.now(timezone.utc),
        ... }
    """

    task_id: str
    status: TaskStatus
    result: Optional[Any]
    error: Optional[str]
    finished_at: datetime
    attempts: int
    last_attempt_at: Optional[datetime]


# Status transition helpers - Optimized for performance

# Immutable cached transition matrix for O(1) lookups
_VALID_TRANSITIONS = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED}
    ),
    TaskStatus.FAILED: frozenset(
        {TaskStatus.PENDING, TaskStatus.CANCELLED}
    ),  # For retries
    TaskStatus.SUCCESS: frozenset(),  # Terminal state
    TaskStatus.CANCELLED: frozenset(),  # Terminal state
}


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """
    Check if a status transition is allowed.

    Optimized with early returns and immutable frozensets for O(1) performance.
    """
    # Early return for no-op transitions (fastest path)
    if from_status == to_status:
        return True

    # O(1) set lookup using cached frozensets
    return to_status in _VALID_TRANSITIONS.get(from_status, frozenset())


def transition_status(task: Task, new_status: TaskStatus) -> Task:
    """Transition a task to a new status if allowed."""
    if not can_transition(task["status"], new_status):
        raise ValueError(
            f"Invalid status transition from {task['status']} to {new_status}"
        )

    # Early return for no-op transition
    if task["status"] == new_status:
        return task

    now = datetime.now(timezone.utc)
    updated_task = task.copy()
    updated_task["status"] = new_status
    updated_task["updated_at"] = now

    # Increment attempts only when transitioning to RUNNING
    if new_status == TaskStatus.RUNNING:
        updated_task["attempts"] += 1
        updated_task["last_attempt_at"] = now

    return updated_task


# Task creation helpers
def create_task(
    func_path: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    eta: Optional[datetime] = None,
    interval: Optional[int | timedelta] = None,
    max_retries: int = 3,
    timeout: Optional[int] = None,
    task_id: Optional[str] = None,
    error: Optional[TaskError] = None,
) -> Task:
    """Create a new task with default values."""
    now = datetime.now(timezone.utc)

    if task_id is None:
        task_id = str(uuid.uuid4())

    if args is None:
        args = []

    if kwargs is None:
        kwargs = {}

    schedule: Schedule = {}
    if eta is not None:
        schedule["eta"] = eta
    if interval is not None:
        # Convert int to timedelta for backward compatibility
        if isinstance(interval, int):
            interval = timedelta(seconds=interval)
        schedule["interval"] = interval

    task: Task = {
        "id": task_id,
        "func_path": func_path,
        "args": args,
        "kwargs": kwargs,
        "status": TaskStatus.PENDING,
        "schedule": schedule,
        "max_retries": max_retries,
        "timeout": timeout,
        "attempts": 0,
        "created_at": now,
        "updated_at": now,
        "last_attempt_at": None,
    }

    # Add error field if provided
    if error is not None:
        task["error"] = error

    return task


def validate_task(task: Task) -> None:
    """Validate that required task fields are set."""
    required_fields = ["id", "func_path", "status", "created_at", "updated_at"]

    for field in required_fields:
        if field not in task or task[field] is None:
            raise ValueError(f"Required field '{field}' is missing or None")

    if not isinstance(task["status"], TaskStatus):
        raise ValueError(f"Invalid status: {task['status']}")

    if not isinstance(task["attempts"], int) or task["attempts"] < 0:
        raise ValueError("attempts must be a non-negative integer")

    if not isinstance(task["max_retries"], int) or task["max_retries"] < 0:
        raise ValueError("max_retries must be a non-negative integer")


# TaskResult creation helpers
def create_success_result(
    task_id: str,
    result: Any,
    attempts: int,
    last_attempt_at: Optional[datetime] = None,
) -> TaskResult:
    """Create a success result for a task."""
    if last_attempt_at is None:
        last_attempt_at = datetime.now(timezone.utc)

    return TaskResult(
        task_id=task_id,
        status=TaskStatus.SUCCESS,
        result=result,
        error=None,
        finished_at=datetime.now(timezone.utc),
        attempts=attempts,
        last_attempt_at=last_attempt_at,
    )


def create_failure_result(
    task_id: str,
    error: str,
    attempts: int,
    last_attempt_at: Optional[datetime] = None,
) -> TaskResult:
    """Create a failure result for a task."""
    if last_attempt_at is None:
        last_attempt_at = datetime.now(timezone.utc)

    return TaskResult(
        task_id=task_id,
        status=TaskStatus.FAILED,
        result=None,
        error=error,
        finished_at=datetime.now(timezone.utc),
        attempts=attempts,
        last_attempt_at=last_attempt_at,
    )


def is_task_due(task: Task) -> bool:
    """Check if a task is due for execution based on its eta."""
    eta = task["schedule"].get("eta")
    if eta is None:
        return True
    return eta <= datetime.now(timezone.utc)


def should_retry(task: Task) -> bool:
    """Check if a task should be retried."""
    return task["attempts"] < task["max_retries"]


def has_interval(task: Task) -> bool:
    """Check if a task has an interval for repeating execution."""
    interval = task["schedule"].get("interval")
    return interval is not None and isinstance(interval, timedelta)


def has_error(task: Task) -> bool:
    """Check if task has an error."""
    return task.get("error") is not None


def is_failed(task: Task) -> bool:
    """Check if task is in failed state."""
    return task["status"] == TaskStatus.FAILED or has_error(task)


def get_error_message(task: Task) -> Optional[str]:
    """Get error message if task has error."""
    error = task.get("error")
    return error.message if error else None
