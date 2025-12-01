from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional

from typing_extensions import NotRequired, TypedDict


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class Schedule(TypedDict):
    eta: NotRequired[Optional[datetime]]
    interval: NotRequired[Optional[timedelta]]  # time interval


class Task(TypedDict):
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


class TaskResult(TypedDict):
    task_id: str
    status: TaskStatus
    result: Optional[Any]
    error: Optional[str]
    finished_at: datetime
    attempts: int
    last_attempt_at: Optional[datetime]


# Status transition helpers
def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if a status transition is allowed."""
    valid_transitions = {
        TaskStatus.PENDING: {
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
        },
        TaskStatus.RUNNING: {
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.RETRYING,
            TaskStatus.CANCELLED,
        },
        TaskStatus.RETRYING: {
            TaskStatus.PENDING,  # Rescheduled for retry
            TaskStatus.RUNNING,  # Picked up for execution
            TaskStatus.CANCELLED,
        },
        TaskStatus.SUCCESS: set(),  # Terminal state
        TaskStatus.FAILED: set(),  # Terminal state
        TaskStatus.CANCELLED: set(),  # Terminal state
    }

    return to_status in valid_transitions.get(from_status, set())


def transition_status(task: Task, new_status: TaskStatus) -> Task:
    """Transition a task to a new status if allowed."""
    if not can_transition(task["status"], new_status):
        raise ValueError(
            f"Invalid status transition from {task['status']} to {new_status}"
        )

    now = datetime.now(timezone.utc)
    updated_task = task.copy()
    updated_task["status"] = new_status
    updated_task["updated_at"] = now

    if new_status in {TaskStatus.RUNNING, TaskStatus.RETRYING}:
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
