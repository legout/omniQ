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

    Key Features:
    - Task persistence and retrieval with proper state management
    - Atomic dequeue operations with claim semantics
    - Retry and interval task support through get_task() and reschedule() methods
    - Result storage and retrieval
    - Efficient cleanup operations for old results

    All storage backends must implement these methods to ensure compatibility
    with the AsyncTaskQueue retry and interval scheduling mechanisms.
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
            will_retry: True if task will be retried (status PENDING),
                       False if final failure (status FAILED)

        Raises:
            NotFoundError: If the task doesn't exist
            StorageError: If the failure cannot be recorded
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Unique task identifier

        Returns:
            Task if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        pass

    @abstractmethod
    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """
        Update a task's ETA for retry or interval rescheduling.

        Args:
            task_id: Unique task identifier
            new_eta: New execution time

        Raises:
            NotFoundError: If task doesn't exist
            StorageError: If update fails
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
    async def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: Optional[int] = None
    ) -> list[Task]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by task status (optional). If None, returns all tasks.
            limit: Maximum number of tasks to return (optional). If None, returns all.

        Returns:
            List of Task dictionaries matching criteria

        Raises:
            StorageError: If task listing fails
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

    @abstractmethod
    async def close(self) -> None:
        """
        Close the storage backend and release resources.

        This method should be called when the storage backend is no longer needed.
        """
        pass


class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class NotFoundError(StorageError):
    """Raised when a requested task or result is not found."""

    pass
