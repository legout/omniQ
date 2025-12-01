"""
AsyncTaskQueue implementation for OmniQ.

This module provides the core task queue functionality that handles
enqueue/dequeue logic, scheduling, and retries separate from
worker and storage concerns.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from .models import (
    Task,
    TaskStatus,
    TaskResult,
    create_task,
    create_success_result,
    create_failure_result,
)
from .storage.base import BaseStorage
from .logging import get_logger


class AsyncTaskQueue:
    """
    Async task queue that handles enqueue/dequeue logic, scheduling, and retries.

    This class separates task queue concerns from worker and storage layers,
    providing a clean interface for task management.

    Features:
    - Task enqueue/dequeue with proper FIFO ordering
    - Scheduling support (ETA and interval tasks)
    - Retry logic with exponential backoff
    - Interval task rescheduling
    - Async operations throughout
    """

    def __init__(self, storage: BaseStorage):
        """
        Initialize AsyncTaskQueue with storage backend.

        Args:
            storage: Storage backend for persistence
        """
        self.storage = storage
        self.logger = get_logger()

    async def enqueue(
        self,
        func_path: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Enqueue a task for execution.

        Args:
            func_path: Function path for execution
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            eta: Scheduled execution time (UTC)
            interval: Interval in seconds for repeating tasks
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds
            task_id: Optional custom task ID

        Returns:
            Task ID for the enqueued task
        """
        kwargs = kwargs or {}

        # Create task with proper scheduling
        task = create_task(
            func_path=func_path,
            args=list(args),  # Convert tuple to list for model
            kwargs=kwargs,
            eta=eta,
            interval=interval,
            max_retries=max_retries or 3,  # Default to 3 if None
            timeout=timeout,
            task_id=task_id,
        )

        # Store task
        task_id = await self.storage.enqueue(task)

        self.logger.info(
            f"Task enqueued: {task_id} -> {func_path}",
            extra={"task_id": task_id, "func_path": func_path},
        )

        return task_id

    async def dequeue(self) -> Optional[Task]:
        """
        Dequeue the next due task.

        Returns:
            Next due task, or None if no tasks are available
        """
        # Get next due task from storage
        now = datetime.now(timezone.utc)
        task = await self.storage.dequeue(now=now)

        if task is None:
            return None

        # Mark task as running in storage
        await self.storage.mark_running(task["id"])

        self.logger.info(f"Task dequeued: {task['id']}", extra={"task_id": task["id"]})

        return task

    async def complete_task(
        self, task_id: str, result: Optional[Any] = None, task: Optional[Task] = None
    ) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: ID of completed task
            result: Task result (optional)
            task: Optional task information for interval rescheduling
        """
        # Create success result
        task_result = create_success_result(task_id, result, attempts=1)

        # Handle interval task rescheduling
        if task and task.get("schedule", {}).get("interval"):
            await self._reschedule_interval_task(task)
        else:
            # Fallback: try to get task by ID (not implemented in BaseStorage yet)
            task_info = await self._get_task_by_id(task_id)
            if task_info and task_info.get("schedule", {}).get("interval"):
                await self._reschedule_interval_task(task_info)

        # Mark task as done
        await self.storage.mark_done(task_id, task_result)

        self.logger.info(f"Task completed: {task_id}", extra={"task_id": task_id})

    async def fail_task(
        self,
        task_id: str,
        error: str,
        exception_type: Optional[str] = None,
        traceback: Optional[str] = None,
        task: Optional[Task] = None,
    ) -> None:
        """
        Mark a task as failed and handle retry logic.

        Args:
            task_id: ID of failed task
            error: Error message
            exception_type: Type of exception
            traceback: Exception traceback
            task: Optional task information for retry logic
        """
        if task is None:
            # Fallback: try to get task by ID (not implemented in BaseStorage yet)
            task = await self._get_task_by_id(task_id)
            if task is None:
                self.logger.warning(f"Task not found for failure: {task_id}")
                return

        # Increment retry count
        new_attempts = task.get("attempts", 0) + 1

        # Check if task should be retried
        if self._should_retry(task, new_attempts):
            # Calculate retry delay with exponential backoff
            retry_delay = self._calculate_retry_delay(new_attempts)
            retry_eta = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)

            # Reschedule task
            await self.storage.reschedule(task_id, retry_eta)

            # Mark as retrying
            await self.storage.mark_failed(task_id, error, will_retry=True)

            self.logger.info(
                f"Task retry scheduled: {task_id} (attempt {new_attempts}) in {retry_delay}s",
                extra={
                    "task_id": task_id,
                    "attempt": new_attempts,
                    "delay": retry_delay,
                },
            )
        else:
            # Mark as finally failed
            await self.storage.mark_failed(task_id, error, will_retry=False)

            self.logger.error(
                f"Task failed permanently: {task_id} after {new_attempts} attempts",
                extra={"task_id": task_id, "attempts": new_attempts, "error": error},
            )

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task object or None if not found
        """
        return await self._get_task_by_id(task_id)

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get the result of a completed task.

        Args:
            task_id: ID of the task

        Returns:
            Task result or None if not available
        """
        return await self.storage.get_result(task_id)

    async def _get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Helper method to get task by ID.

        This is a placeholder since BaseStorage doesn't have get_task method.
        In a real implementation, this would be added to BaseStorage.
        """
        # For now, we'll work with the task info we have
        # This would need to be implemented in BaseStorage
        return None

    async def _reschedule_interval_task(self, task: Task) -> None:
        """
        Reschedule an interval task for its next execution.

        Args:
            task: Completed interval task
        """
        # Calculate next execution time
        next_eta = datetime.now(timezone.utc) + timedelta(
            seconds=task.get("interval", 0)
        )

        # Create new task instance for next execution
        next_task = create_task(
            func_path=task.get("func_path", ""),
            args=task.get("args", []),
            kwargs=task.get("kwargs", {}),
            eta=next_eta,
            interval=task.get("interval"),
            max_retries=task.get("max_retries", 3),
            timeout=task.get("timeout"),
        )

        # Enqueue next execution
        await self.storage.enqueue(next_task)

        self.logger.info(
            f"Interval task rescheduled: {task.get('id')} -> {next_task['id']} in {task.get('interval')}s",
            extra={
                "current_task_id": task.get("id"),
                "next_task_id": next_task["id"],
                "interval": task.get("interval"),
            },
        )

    def _should_retry(self, task: Task, attempts: int) -> bool:
        """
        Determine if a task should be retried.

        Args:
            task: Task to check
            attempts: Current attempt count

        Returns:
            True if task should be retried
        """
        max_retries = task.get("max_retries", 3)
        return attempts < max_retries

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """
        Calculate retry delay with exponential backoff and jitter.

        Args:
            retry_count: Current retry attempt (1-based)

        Returns:
            Delay in seconds
        """
        # Base delay: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        base_delay = min(2 ** (retry_count - 1), 60)

        # Add jitter: ±25% random variation
        jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
        delay = base_delay * jitter_factor

        return delay
