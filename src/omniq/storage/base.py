from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from ..models import Task, TaskResult, TaskStatus


class BaseStorage(ABC):
    """
    Async storage interface for queue and result operations used by the task queue and worker pool.

    This interface provides the contract for all storage backends, ensuring consistent
    behavior across different implementations (file, SQLite, Redis, etc.).
    """

    @abstractmethod
    async def enqueue(self, task: Task) -> str:
        """
        Persist a task and make it eligible for dequeue when its eta is due.

        Args:
            task: The task to persist

        Returns:
            The task ID

        Raises:
            StorageError: If the task cannot be persisted
        """
        pass

    @abstractmethod
    async def dequeue(self, now: datetime) -> Optional[Task]:
        """
        Retrieve a single due task, ensuring atomic claim semantics.

        Args:
            now: Current time for eta comparison

        Returns:
            A due task if available, None otherwise

        Note:
            - Returns at most one task with eta <= now
            - Prefers earliest eta for ordering
            - Uses FIFO ordering for tasks with same eta when practical
            - Once returned, the task must not be returned again unless rescheduled
        """
        pass

    @abstractmethod
    async def mark_running(self, task_id: str) -> None:
        """
        Update task status to RUNNING and update timestamps.

        Args:
            task_id: ID of the task to mark as running

        Raises:
            NotFoundError: If the task doesn't exist
            StorageError: If the status cannot be updated
        """
        pass

    @abstractmethod
    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """
        Persist a successful result and update task status to SUCCESS.

        Args:
            task_id: ID of the completed task
            result: The task result to persist

        Raises:
            NotFoundError: If the task doesn't exist
            StorageError: If the result cannot be persisted
        """
        pass

    @abstractmethod
    async def mark_failed(self, task_id: str, error: str, will_retry: bool) -> None:
        """
        Record a failure and update task status appropriately.

        Args:
            task_id: ID of the failed task
            error: Error description or exception details
            will_retry: True if task will be retried (status RETRYING),
                       False if final failure (status FAILED)

        Raises:
            NotFoundError: If the task doesn't exist
            StorageError: If the failure cannot be recorded
        """
        pass

    @abstractmethod
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Retrieve a task result by ID.

        Args:
            task_id: ID of the task to get result for

        Returns:
            The task result if it exists, None otherwise
        """
        pass

    @abstractmethod
    async def purge_results(self, older_than: datetime) -> int:
        """
        Remove old results based on age.

        Args:
            older_than: Cutoff timestamp - results older than this are removed

        Returns:
            Count of results that were purged
        """
        pass

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """
        Update a task's eta for future execution.

        Args:
            task_id: ID of the task to reschedule
            new_eta: New execution time

        Raises:
            NotImplementedError: If the backend doesn't support rescheduling
            NotFoundError: If the task doesn't exist
            StorageError: If the task cannot be rescheduled
        """
        raise NotImplementedError("This storage backend does not support rescheduling")


class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class NotFoundError(StorageError):
    """Raised when a requested task or result is not found."""

    pass
