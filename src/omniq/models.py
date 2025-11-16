from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, Union


class TaskStatus(str, Enum):
    """Task status enumeration with allowed transitions."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Schedule:
    """Simple scheduling configuration for tasks."""

    def __init__(
        self,
        eta: datetime,
        interval: Optional[int] = None,
        max_retries: int = 0,
        timeout: Optional[int] = None,
    ):
        self.eta = eta
        self.interval = interval  # Fixed interval in seconds for recurring tasks
        self.max_retries = max_retries
        self.timeout = timeout

    def is_due(self, now: Optional[datetime] = None) -> bool:
        """Check if task is due for execution."""
        if now is None:
            now = datetime.now(timezone.utc)
        return now >= self.eta


class TaskResult:
    """Result of task execution."""

    def __init__(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Any] = None,
        error: Optional[Exception] = None,
        attempt: int = 1,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.status = status
        self.result = result
        self.error = error
        self.attempt = attempt
        self.started_at = started_at
        self.completed_at = completed_at

    @classmethod
    def success(
        cls, task_id: str, result: Any, attempt: int = 1, **kwargs
    ) -> TaskResult:
        """Create a successful task result."""
        now = datetime.now(timezone.utc)
        return cls(
            task_id=task_id,
            status=TaskStatus.SUCCESS,
            result=result,
            attempt=attempt,
            started_at=kwargs.get("started_at", now),
            completed_at=now,
        )

    @classmethod
    def failure(
        cls, task_id: str, error: Exception, attempt: int = 1, **kwargs
    ) -> TaskResult:
        """Create a failed task result."""
        now = datetime.now(timezone.utc)
        return cls(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error,
            attempt=attempt,
            started_at=kwargs.get("started_at", now),
            completed_at=now,
        )

    @classmethod
    def retrying(
        cls, task_id: str, error: Exception, attempt: int, next_eta: datetime
    ) -> TaskResult:
        """Create a retrying task result."""
        return cls(
            task_id=task_id,
            status=TaskStatus.RETRYING,
            error=error,
            attempt=attempt,
        )


class Task:
    """Core task representation."""

    def __init__(
        self,
        id: str,
        func_path: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        schedule: Optional[Schedule] = None,
        status: TaskStatus = TaskStatus.PENDING,
        attempt: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.func_path = func_path
        self.args = args
        self.kwargs = kwargs or {}
        self.schedule = schedule or Schedule(eta=datetime.now(timezone.utc))
        self.status = status
        self.attempt = attempt
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.metadata = metadata or {}

    @classmethod
    def create(
        cls,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: int = 0,
        timeout: Optional[int] = None,
        task_id: Optional[str] = None,
        schedule: Optional[Schedule] = None,
    ) -> Task:
        """Create a task from a Python callable."""
        if task_id is None:
            task_id = str(uuid.uuid4())

        if schedule is None:
            schedule = Schedule(
                eta=eta or datetime.now(timezone.utc),
                interval=interval,
                max_retries=max_retries,
                timeout=timeout,
            )

        func_path = f"{func.__module__}.{func.__qualname__}"

        return cls(
            id=task_id,
            func_path=func_path,
            args=args,
            kwargs=kwargs or {},
            schedule=schedule,
        )

    def validate(self) -> None:
        """Validate task has all required fields."""
        if not self.id:
            raise ValueError("Task ID is required")
        if not self.func_path:
            raise ValueError("Function path is required")
        if self.schedule.eta is None:
            raise ValueError("Schedule ETA is required")

    def to_running(self) -> Task:
        """Transition task to running status."""
        updated = self._copy()
        updated.status = TaskStatus.RUNNING
        updated.updated_at = datetime.now(timezone.utc)
        return updated

    def to_success(self) -> Task:
        """Transition task to success status."""
        updated = self._copy()
        updated.status = TaskStatus.SUCCESS
        updated.updated_at = datetime.now(timezone.utc)
        return updated

    def to_failed(self) -> Task:
        """Transition task to failed status."""
        updated = self._copy()
        updated.status = TaskStatus.FAILED
        updated.updated_at = datetime.now(timezone.utc)
        return updated

    def to_retrying(self, next_eta: datetime) -> Task:
        """Transition task to retrying status."""
        updated = self._copy()
        updated.status = TaskStatus.RETRYING
        updated.schedule = Schedule(
            eta=next_eta,
            interval=self.schedule.interval,
            max_retries=self.schedule.max_retries,
            timeout=self.schedule.timeout,
        )
        updated.attempt += 1
        updated.updated_at = datetime.now(timezone.utc)
        return updated

    def to_cancelled(self) -> Task:
        """Transition task to cancelled status."""
        updated = self._copy()
        updated.status = TaskStatus.CANCELLED
        updated.updated_at = datetime.now(timezone.utc)
        return updated

    def can_retry(self) -> bool:
        """Check if task can be retried based on attempt count."""
        return self.attempt <= self.schedule.max_retries

    def is_due(self, now: Optional[datetime] = None) -> bool:
        """Check if task is due for execution."""
        return self.schedule.is_due(now)

    def _copy(self) -> Task:
        """Create a copy of the task with updated timestamp."""
        return Task(
            id=self.id,
            func_path=self.func_path,
            args=self.args,
            kwargs=self.kwargs,
            schedule=self.schedule,
            status=self.status,
            attempt=self.attempt,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=self.metadata.copy() if self.metadata else None,
        )


# Status transition helper functions
def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if a status transition is allowed."""
    allowed_transitions = {
        TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.RETRYING,
            TaskStatus.CANCELLED,
        },
        TaskStatus.RETRYING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.SUCCESS: set(),  # Terminal state
        TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.CANCELLED},
        TaskStatus.CANCELLED: set(),  # Terminal state
    }

    return to_status in allowed_transitions.get(from_status, set())


def validate_transition(task: Task, new_status: TaskStatus) -> None:
    """Validate that a status transition is allowed."""
    if not can_transition(task.status, new_status):
        raise ValueError(f"Invalid transition from {task.status} to {new_status}")
