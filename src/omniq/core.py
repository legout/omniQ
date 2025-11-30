from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from .config import Settings
from .models import Task, TaskResult, create_task
from .storage.base import BaseStorage
from .storage.file import FileStorage
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

        # Configure logging
        from .logging import configure_logging

        configure_logging(self.settings.log_level)

        # Initialize storage backend
        self._storage = self._create_storage()

        self.logger = get_logger()

    def _create_storage(self) -> BaseStorage:
        """Create storage backend based on settings."""
        serializer = self.settings.create_serializer()

        if self.settings.backend.value == "file":
            return FileStorage(self.settings.base_dir, serializer)
        elif self.settings.backend.value == "sqlite":
            # SQLite storage will be implemented in a future change
            raise NotImplementedError("SQLite backend is not yet implemented")
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

        # Enqueue to storage
        task_id = await self._storage.enqueue(task)

        # Log enqueuing
        log_task_enqueued(task_id, func_path)

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
            return await self._storage.get_result(task_id)

    def worker(self, concurrency: int = 1) -> AsyncWorkerPool:
        """
        Create a worker pool for processing tasks.

        Args:
            concurrency: Number of concurrent workers

        Returns:
            AsyncWorkerPool instance
        """
        return AsyncWorkerPool(self._storage, concurrency)


class AsyncWorkerPool:
    """
    Async worker pool for processing tasks from storage.

    Note: This is a placeholder implementation. The full worker pool
    will be implemented in the add-async-worker-pool change.
    """

    def __init__(self, storage: BaseStorage, concurrency: int = 1):
        self.storage = storage
        self.concurrency = concurrency
        self._running = False
        self.logger = get_logger()

    async def start(self) -> None:
        """Start the worker pool."""
        self._running = True
        log_worker_started(self.concurrency)

        # Simple task processing loop
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                task = await self.storage.dequeue(now)

                if task is not None:
                    await self._process_task(task)
                else:
                    # No tasks available, wait a bit
                    await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def stop(self) -> None:
        """Stop the worker pool."""
        self._running = False
        log_worker_stopped()

    async def _process_task(self, task: Task) -> None:
        """Process a single task."""
        task_id = task["id"]
        func_path = task["func_path"]

        log_task_started(task_id, task["attempts"] + 1)

        try:
            # Import and execute function
            module_name, func_name = func_path.rsplit(".", 1)
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)

            # Execute function
            if inspect.iscoroutinefunction(func):
                result = await func(*task["args"], **task["kwargs"])
            else:
                result = func(*task["args"], **task["kwargs"])

            # Create success result
            from .models import create_success_result

            task_result = create_success_result(
                task_id=task_id,
                result=result,
                attempts=task["attempts"] + 1,
                last_attempt_at=datetime.now(timezone.utc),
            )

            # Mark as done
            await self.storage.mark_done(task_id, task_result)
            log_task_completed(task_id, task["attempts"] + 1)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"

            # Determine if should retry
            will_retry = task["attempts"] < task["max_retries"]

            # Mark as failed
            await self.storage.mark_failed(task_id, error_msg, will_retry)
            log_task_failed(task_id, error_msg, will_retry)


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

    def worker(self, concurrency: int = 1) -> SyncWorkerPool:
        """
        Create a synchronous worker pool.

        Args:
            concurrency: Number of concurrent workers

        Returns:
            SyncWorkerPool instance
        """
        return SyncWorkerPool(self._async_omniq, concurrency)


class SyncWorkerPool:
    """
    Synchronous wrapper for AsyncWorkerPool.

    Runs the async worker pool in a dedicated thread.
    """

    def __init__(self, async_omniq: AsyncOmniQ, concurrency: int = 1):
        self.async_omniq = async_omniq
        self.concurrency = concurrency
        self._worker = None
        self._thread = None

    def start(self) -> None:
        """Start the worker pool (blocking)."""
        import threading

        def run_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            worker = self.async_omniq.worker(self.concurrency)
            self._worker = worker
            loop.run_until_complete(worker.start())

        self._thread = threading.Thread(target=run_worker, daemon=True)
        self._thread.start()
        self._thread.join()  # Wait for worker to finish

    def stop(self) -> None:
        """Stop the worker pool."""
        if self._worker:
            # This is a simplified stop - in practice would need thread-safe communication
            self._worker._running = False
