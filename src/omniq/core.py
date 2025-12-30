from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from .config import Settings
from .models import Task, TaskResult, TaskError, TaskStatus, create_task
from .storage.base import BaseStorage
from .storage.file import FileStorage
from .storage.sqlite import SQLiteStorage
from .queue import AsyncTaskQueue
from .worker import AsyncWorkerPool, WorkerPool
from .logging import (
    get_logger,
    log_task_enqueued,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_worker_started,
    log_worker_stopped,
)


class AsyncOmniQ:
    """
    Async-first façade for OmniQ task queue operations.

    Provides the primary interface for enqueuing tasks, retrieving results,
    and creating workers in async contexts.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize AsyncOmniQ with settings.

        Args:
            settings: Configuration settings. If None, uses Settings.from_env().
        """
        self.settings = settings or Settings.from_env()
        self.settings.validate()

        # Logging is configured automatically on import

        # Initialize storage backend
        self._storage = self._create_storage()

        # Initialize task queue
        self._queue = AsyncTaskQueue(self._storage)

        self.logger = get_logger()

    def _create_storage(self) -> BaseStorage:
        """Create storage backend based on settings."""
        serializer = self.settings.create_serializer()

        if self.settings.backend.value == "file":
            return FileStorage(self.settings.base_dir, serializer)
        elif self.settings.backend.value == "sqlite":
            if self.settings.db_url:
                return SQLiteStorage(db_url=self.settings.db_url)
            else:
                # Fallback to default path for backward compatibility
                return SQLiteStorage(db_path=self.settings.base_dir / "omniq.db")
        else:
            raise ValueError(f"Unknown backend: {self.settings.backend}")

    async def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Enqueue a task for execution.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            eta: Optional scheduled execution time
            interval: Optional interval for repeating tasks (seconds)
            max_retries: Maximum retry attempts (overrides settings default)
            timeout: Task timeout in seconds (overrides settings default)
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID for the enqueued task

        Example:
            >>> async def send_email(to: str, subject: str, body: str) -> str:
            ...     # Simulated email sending
            ...     return f"Email sent to {to}"
            >>>
            >>> # Enqueue a simple task
            >>> task_id = await omniq.enqueue(
            ...     send_email,
            ...     "user@example.com",
            ...     subject="Welcome",
            ...     body="Hello!"
            ... )
            >>>
            >>> # Enqueue with custom timeout
            >>> task_id = await omniq.enqueue(
            ...     send_email,
            ...     "user@example.com",
            ...     subject="Report",
            ...     body="Your report is ready",
            ...     timeout=60  # 1 minute timeout
            ... )
        """
        # Extract function path
        func_path = f"{func.__module__}.{func.__qualname__}"

        # Use settings defaults if not provided
        if max_retries is None:
            max_retries = self.settings.default_max_retries
        if timeout is None:
            timeout = self.settings.default_timeout

        # Enqueue to task queue
        task_id = await self._queue.enqueue(
            func_path=func_path,
            args=args,
            kwargs=kwargs,
            eta=eta,
            interval=interval,
            max_retries=max_retries,
            timeout=timeout,
        )

        return task_id

    async def get_result(
        self,
        task_id: str,
        wait: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[TaskResult]:
        """Get the result of a task.

        Args:
            task_id: ID of the task to get result for
            wait: Whether to wait for result if not available
            timeout: Maximum time to wait (seconds)

        Returns:
            TaskResult if available, None otherwise

        Example:
            >>> # Get result immediately
            >>> result = await omniq.get_result("task-id-123")
            >>> if result:
            ...     if result.status == TaskStatus.SUCCESS:
            ...         print(f"Result: {result.result}")
            ...     else:
            ...         print(f"Error: {result.error}")
            >>>
            >>> # Wait for result with timeout
            >>> result = await omniq.get_result(
            ...     "task-id-123",
            ...     wait=True,
            ...     timeout=30.0
            ... )
            >>> if result:
            ...     print(f"Task completed after {result.attempts} attempts")
        """
        if wait:
            # Simple polling implementation for waiting
            start_time = asyncio.get_event_loop().time()
            while True:
                result = await self._storage.get_result(task_id)
                if result is not None:
                    return result

                # Check timeout
                if timeout is not None:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= timeout:
                        return None

                # Poll interval (100ms)
                await asyncio.sleep(0.1)
        else:
            return await self._queue.get_result(task_id)

    async def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: Optional[int] = 25
    ) -> list[Task]:
        """List tasks with optional filtering.

        Args:
            status: Filter by task status (optional). If None, returns all tasks.
            limit: Maximum number of tasks to return (optional, default 25). If None, returns all.

        Returns:
            List of Task dictionaries matching criteria

        Example:
            >>> # List all tasks
            >>> tasks = await omniq.list_tasks()
            >>>
            >>> # List only pending tasks
            >>> pending = await omniq.list_tasks(status=TaskStatus.PENDING)
            >>>
            >>> # List last 10 failed tasks
            >>> failed = await omniq.list_tasks(status=TaskStatus.FAILED, limit=10)
        """
        return await self._storage.list_tasks(status=status, limit=limit)

    def worker(
        self, concurrency: int = 1, poll_interval: float = 1.0
    ) -> AsyncWorkerPool:
        """Create a worker pool for processing tasks.

        Args:
            concurrency: Number of concurrent workers
            poll_interval: Seconds between storage polls when idle

        Returns:
            AsyncWorkerPool instance

        Example:
            >>> # Create a single worker
            >>> worker_pool = omniq.worker()
            >>> async with worker_pool:
            ...     await worker_pool.run()  # Runs until cancelled
            >>>
            >>> # Create multiple concurrent workers
            >>> worker_pool = omniq.worker(concurrency=4)
            >>> async with worker_pool:
            ...     await worker_pool.run()
        """
        return AsyncWorkerPool(
            queue=self._queue, concurrency=concurrency, poll_interval=poll_interval
        )

    @classmethod
    def from_env(cls) -> AsyncOmniQ:
        """
        Create AsyncOmniQ from environment variables.

        Uses Settings.from_env() to create configuration from environment variables.

        Returns:
            AsyncOmniQ instance configured from environment
        """
        settings = Settings.from_env()
        return cls(settings=settings)


class OmniQ:
    """
    Synchronous façade for OmniQ operations.

    Provides blocking wrappers around async methods for use in
    synchronous code contexts.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize OmniQ with settings.

        Args:
            settings: Configuration settings. If None, uses Settings.from_env().
        """
        self._async_omniq = AsyncOmniQ(settings)
        self._loop = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create an event loop for sync operations."""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        """Run an async coroutine in the dedicated loop."""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Enqueue a task for execution (blocking).

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            eta: Optional scheduled execution time
            interval: Optional interval for repeating tasks (seconds)
            max_retries: Maximum retry attempts (overrides settings default)
            timeout: Task timeout in seconds (overrides settings default)
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID for the enqueued task
        """
        coro = self._async_omniq.enqueue(
            func,
            *args,
            eta=eta,
            interval=interval,
            max_retries=max_retries,
            timeout=timeout,
            **kwargs,
        )
        return self._run_async(coro)

    def get_result(
        self,
        task_id: str,
        wait: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[TaskResult]:
        """
        Get the result of a task (blocking).

        Args:
            task_id: ID of the task to get result for
            wait: Whether to wait for result if not available
            timeout: Maximum time to wait (seconds)

        Returns:
            TaskResult if available, None otherwise
        """
        coro = self._async_omniq.get_result(task_id, wait, timeout)
        return self._run_async(coro)

    def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: Optional[int] = 25
    ) -> list[Task]:
        """List tasks with optional filtering (blocking).

        Args:
            status: Filter by task status (optional). If None, returns all tasks.
            limit: Maximum number of tasks to return (optional, default 25). If None, returns all.

        Returns:
            List of Task dictionaries matching criteria

        Example:
            >>> # List all tasks
            >>> tasks = omniq.list_tasks()
            >>>
            >>> # List only pending tasks
            >>> pending = omniq.list_tasks(status=TaskStatus.PENDING)
        """
        coro = self._async_omniq.list_tasks(status=status, limit=limit)
        return self._run_async(coro)

    def worker(self, concurrency: int = 1, poll_interval: float = 1.0) -> WorkerPool:
        """
        Create a synchronous worker pool.

        Args:
            concurrency: Number of concurrent workers
            poll_interval: Seconds between storage polls when idle

        Returns:
            WorkerPool instance
        """
        return WorkerPool(
            queue=self._async_omniq._queue,
            concurrency=concurrency,
            poll_interval=poll_interval,
        )

    @classmethod
    def from_env(cls) -> OmniQ:
        """
        Create OmniQ from environment variables.

        Uses Settings.from_env() to create configuration from environment variables.

        Returns:
            OmniQ instance configured from environment
        """
        settings = Settings.from_env()
        return cls(settings=settings)
