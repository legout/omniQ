from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from .config import Settings
from .models import Task, TaskResult, TaskError, create_task
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
            return SQLiteStorage(self.settings.base_dir / "omniq.db")
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
        """
        Enqueue a task for execution.

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
        # Extract function path
        func_path = f"{func.__module__}.{func.__qualname__}"

        # Use settings defaults if not provided
        if max_retries is None:
            max_retries = self.settings.default_max_retries
        if timeout is None:
            timeout = self.settings.default_timeout

        # Create task (ensure max_retries is not None)
        task = create_task(
            func_path=func_path,
            args=list(args),
            kwargs=kwargs,
            eta=eta,
            interval=interval,
            max_retries=max_retries or self.settings.default_max_retries,
            timeout=timeout,
        )

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
        """
        Get the result of a task.

        Args:
            task_id: ID of the task to get result for
            wait: Whether to wait for result if not available
            timeout: Maximum time to wait (seconds)

        Returns:
            TaskResult if available, None otherwise
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

    def worker(
        self, concurrency: int = 1, poll_interval: float = 1.0
    ) -> AsyncWorkerPool:
        """
        Create a worker pool for processing tasks.

        Args:
            concurrency: Number of concurrent workers
            poll_interval: Seconds between storage polls when idle

        Returns:
            AsyncWorkerPool instance
        """
        return AsyncWorkerPool(self._queue, concurrency, poll_interval)


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

    def worker(self, concurrency: int = 1, poll_interval: float = 1.0) -> WorkerPool:
        """
        Create a synchronous worker pool.

        Args:
            concurrency: Number of concurrent workers
            poll_interval: Seconds between storage polls when idle

        Returns:
            WorkerPool instance
        """
        return WorkerPool(self._async_omniq._storage, concurrency, poll_interval)
