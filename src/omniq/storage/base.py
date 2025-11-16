"""Storage package for OmniQ task and result persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol

from ..models import Task, TaskResult


class TaskError(Exception):
    """Task execution error wrapper."""

    def __init__(self, error: Exception):
        self.error = error
        super().__init__(str(error))


class BaseStorage(ABC):
    """Abstract storage interface for OmniQ tasks and results.

    All methods are async to align with the async-first core design.
    """

    @abstractmethod
    async def enqueue(self, task: Task) -> str:
        """Add a task to the queue.

        Args:
            task: The task to enqueue

        Returns:
            The task ID (should match task.id)

        Raises:
            Any storage-specific errors
        """
        ...

    @abstractmethod
    async def dequeue(self, now: datetime) -> Optional[Task]:
        """Get the next due task from the queue.

        Args:
            now: Current time to use for ETA comparison

        Returns:
            The next due task, or None if no tasks are due

        Notes:
            - Returns at most one task with eta <= now
            - Should prefer tasks with earliest ETA
            - Uses FIFO for tasks with same ETA
            - Task must not be returned again unless rescheduled
        """
        ...

    @abstractmethod
    async def mark_running(self, task_id: str) -> None:
        """Mark a task as running.

        Args:
            task_id: ID of the task to mark as running

        Notes:
            May be a no-op if dequeue already implies running state
        """
        ...

    @abstractmethod
    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """Mark a task as completed successfully.

        Args:
            task_id: ID of the completed task
            result: The task execution result
        """
        ...

    @abstractmethod
    async def mark_failed(
        self, task_id: str, error: TaskError, will_retry: bool
    ) -> None:
        """Mark a task as failed.

        Args:
            task_id: ID of the failed task
            error: The execution error
            will_retry: True if task will be retried (RETRYING status),
                       False if final failure (FAILED status)
        """
        ...

    @abstractmethod
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve the result of a completed task.

        Args:
            task_id: ID of the task to get results for

        Returns:
            The task result, or None if not found
        """
        ...

    @abstractmethod
    async def purge_results(self, older_than: datetime) -> int:
        """Remove old task results to save space.

        Args:
            older_than: Remove results completed before this time

        Returns:
            Number of results purged
        """
        ...

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Reschedule a task to run at a different time.

        Args:
            task_id: ID of the task to reschedule
            new_eta: New scheduled execution time

        Raises:
            NotImplementedError: If backend doesn't support rescheduling
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support rescheduling"
        )

    @abstractmethod
    async def close(self) -> None:
        """Close any open resources."""
        ...


class Serializer(Protocol):
    """Protocol for task serialization."""

    async def encode_task(self, task: Task) -> bytes:
        """Encode a task to bytes."""
        ...

    async def decode_task(self, data: bytes) -> Task:
        """Decode bytes to a task."""
        ...

    async def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result to bytes."""
        ...

    async def decode_result(self, data: bytes) -> TaskResult:
        """Decode bytes to a result."""
        ...
