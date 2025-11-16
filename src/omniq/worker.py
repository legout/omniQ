"""Worker pool implementation for OmniQ task execution."""

from __future__ import annotations

import asyncio
import functools
import importlib
import inspect
import random
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Set

from loguru import logger
from .models import Task, TaskResult, TaskStatus, Schedule
from .storage.base import BaseStorage, TaskError
from .storage.file import FileStorage
from .storage.sqlite import SQLiteStorage


class AsyncWorkerPool:
    """Async worker pool for processing OmniQ tasks.

    The worker pool polls storage for due tasks and executes them with
    configurable concurrency limits. It handles retries, backoff, and
    graceful shutdown.
    """

    def __init__(
        self,
        storage: BaseStorage,
        concurrency: int = 1,
        poll_interval: float = 1.0,
        base_retry_delay: float = 1.0,
    ):
        """Initialize AsyncWorkerPool.

        Args:
            storage: Storage backend for task operations
            concurrency: Maximum number of concurrent tasks
            poll_interval: Seconds to wait between polls when no work is available
            base_retry_delay: Base delay for exponential backoff (seconds)
        """
        self.storage = storage
        self.concurrency = max(1, concurrency)
        self.poll_interval = max(0.1, poll_interval)
        self.base_retry_delay = base_retry_delay

        self._running = False
        self._in_flight: Set[asyncio.Task] = set()
        self._callable_cache: dict[str, Callable] = {}

        # Thread pool for sync function execution
        self._executor = None

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            logger.warning("Worker pool already running")
            return

        self._running = True
        self._executor = asyncio.get_event_loop()
        logger.info(f"Starting AsyncWorkerPool with concurrency={self.concurrency}")

        try:
            await self._run_loop()
        finally:
            self._running = False
            # Cancel any remaining in-flight tasks
            for task in self._in_flight:
                if not task.done():
                    task.cancel()

            if self._in_flight:
                await asyncio.gather(*self._in_flight, return_exceptions=True)

            logger.info("AsyncWorkerPool stopped")

    async def stop(self, cancel_in_flight: bool = False) -> None:
        """Stop the worker pool.

        Args:
            cancel_in_flight: If True, cancel in-flight tasks immediately.
                            If False, allow them to complete gracefully.
        """
        self._running = False

        if cancel_in_flight:
            # Cancel all in-flight tasks
            for task in self._in_flight:
                if not task.done():
                    task.cancel()
        else:
            # Wait for in-flight tasks to complete
            if self._in_flight:
                logger.info(
                    f"Waiting for {len(self._in_flight)} in-flight tasks to complete"
                )
                await asyncio.gather(*self._in_flight, return_exceptions=True)

    async def _run_loop(self) -> None:
        """Main worker loop."""
        logger.info("Worker loop started")

        while self._running:
            try:
                # Fill available worker slots
                await self._poll_and_execute()

                # Wait before next poll if no work available
                if not self._in_flight:
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(self.poll_interval)

    async def _poll_and_execute(self) -> None:
        """Poll storage for tasks and execute available ones."""
        now = datetime.now(timezone.utc)

        # Fill available slots up to concurrency limit
        while len(self._in_flight) < self.concurrency and self._running:
            task = await self.storage.dequeue(now)
            if task is None:
                break

            # Execute task
            exec_task = asyncio.create_task(self._execute_task(task))
            self._in_flight.add(exec_task)

            # Clean up when task completes
            exec_task.add_done_callback(self._in_flight.discard)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task.

        Args:
            task: The task to execute
        """
        task_id = task.id
        func_name = task.func_path

        try:
            logger.info(f"Starting task {task_id}: {func_name}")

            # Mark task as running
            await self.storage.mark_running(task_id)

            # Resolve and execute the callable
            result = await self._execute_callable(task)

            # Create success result
            task_result = TaskResult.success(task_id, result, attempt=task.attempt)

            # Mark task as done
            await self.storage.mark_done(task_id, task_result)

            logger.info(f"Task {task_id} completed successfully")

            # Handle interval tasks (reschedule for next run)
            if task.schedule.interval is not None:
                await self._reschedule_interval_task(task)

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self._handle_task_failure(task, e)

    async def _execute_callable(self, task: Task) -> Any:
        """Execute the task's callable.

        Args:
            task: The task containing the callable to execute

        Returns:
            The result of the callable execution
        """
        # Resolve callable from func_path
        callable_func = await self._resolve_callable(task.func_path)

        # Check if callable is async
        if inspect.iscoroutinefunction(callable_func):
            # Execute async function
            return await callable_func(*task.args, **task.kwargs)
        else:
            # Execute sync function in thread pool
            func_call = functools.partial(callable_func, *task.args, **task.kwargs)
            return await asyncio.get_event_loop().run_in_executor(None, func_call)

    async def _resolve_callable(self, func_path: str) -> Callable:
        """Resolve a callable from its module.path string.

        Args:
            func_path: Dotted path to the callable (e.g., 'module.function')

        Returns:
            The resolved callable function

        Raises:
            ImportError: If the module cannot be imported
            AttributeError: If the function cannot be found
        """
        # Check cache first
        if func_path in self._callable_cache:
            return self._callable_cache[func_path]

        # Import module and get function
        module_name, func_name = func_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        callable_func = getattr(module, func_name)

        # Cache for future use
        self._callable_cache[func_path] = callable_func
        return callable_func

    async def _handle_task_failure(self, task: Task, error: Exception) -> None:
        """Handle task execution failure with retry logic.

        Args:
            task: The failed task
            error: The exception that occurred
        """
        task_id = task.id
        max_retries = task.schedule.max_retries
        current_attempt = task.attempt

        # Create error result
        task_error = TaskError(error)

        if current_attempt <= max_retries:
            # Schedule retry with exponential backoff
            retry_delay = self._calculate_retry_delay(current_attempt)
            new_eta = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)

            logger.info(
                f"Task {task_id} will retry (attempt {current_attempt}/{max_retries}) "
                f"in {retry_delay:.1f} seconds"
            )

            # Mark as retrying and reschedule
            await self.storage.mark_failed(task_id, task_error, will_retry=True)
            await self.storage.reschedule(task_id, new_eta)

        else:
            # Final failure
            logger.error(
                f"Task {task_id} failed permanently after {current_attempt} attempts"
            )

            await self.storage.mark_failed(task_id, task_error, will_retry=False)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay using exponential backoff with jitter.

        Args:
            attempt: The attempt number (1-based)

        Returns:
            Delay in seconds before the next retry
        """
        # Exponential backoff: base_delay * (2 ** (attempt - 1))
        base_delay = self.base_retry_delay * (2 ** (attempt - 1))

        # Add jitter: ±10% of the base delay
        jitter_range = base_delay * 0.1
        jitter = random.uniform(-jitter_range, jitter_range)

        delay = max(0.1, base_delay + jitter)  # Minimum 100ms delay
        return delay

    async def _reschedule_interval_task(self, task: Task) -> None:
        """Reschedule a task with an interval for its next run.

        Args:
            task: The completed interval task
        """
        if task.schedule.interval is None:
            return

        # Calculate next ETA (from completion time, not original ETA)
        next_eta = datetime.now(timezone.utc) + timedelta(
            seconds=task.schedule.interval
        )

        # Create a new task ID for the next run (or reuse if backend supports it)
        # For now, we'll reuse the same task ID as a simplification
        logger.debug(f"Rescheduling interval task {task.id} for {next_eta}")

        try:
            await self.storage.reschedule(task.id, next_eta)
        except Exception as e:
            logger.warning(f"Failed to reschedule interval task {task.id}: {e}")


class WorkerPool:
    """Synchronous wrapper for AsyncWorkerPool.

    This provides a blocking interface for users who prefer synchronous
    operations while running the async worker pool in a dedicated thread.
    """

    def __init__(
        self,
        storage: BaseStorage,
        concurrency: int = 1,
        poll_interval: float = 1.0,
        base_retry_delay: float = 1.0,
    ):
        """Initialize WorkerPool.

        Args:
            storage: Storage backend for task operations
            concurrency: Maximum number of concurrent tasks
            poll_interval: Seconds to wait between polls when no work is available
            base_retry_delay: Base delay for exponential backoff (seconds)
        """
        self._async_pool = AsyncWorkerPool(
            storage, concurrency, poll_interval, base_retry_delay
        )
        self._thread = None
        self._running = False

    def start(self) -> None:
        """Start the worker pool (blocking).

        This method blocks until the worker pool is stopped.
        """
        if self._running:
            logger.warning("Worker pool already running")
            return

        self._running = True
        self._stop_event = asyncio.Event()

        def run_worker():
            """Run the async worker pool in an event loop."""
            try:
                asyncio.run(self._run_async())
            except Exception as e:
                logger.error(f"Error in worker thread: {e}", exc_info=True)

        self._thread = threading.Thread(target=run_worker, daemon=True)
        self._thread.start()

        # Wait briefly to ensure the worker starts
        time.sleep(0.1)
        logger.info("WorkerPool started")

    async def _run_async(self) -> None:
        """Run the async worker pool with stop event handling."""
        # Start the async pool
        await self._async_pool.start()

        # Wait for stop signal
        await self._stop_event.wait()

    def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker pool.

        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        if not self._running:
            return

        self._running = False
        logger.info("Stopping WorkerPool")

        # Signal the async side to stop by setting a flag
        self._stop_event.set()

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        logger.info("WorkerPool stopped")


def create_worker_pool(
    storage: Optional[BaseStorage] = None,
    concurrency: int = 1,
    poll_interval: float = 1.0,
    base_retry_delay: float = 1.0,
    sync: bool = False,
) -> AsyncWorkerPool | WorkerPool:
    """Create a worker pool instance.

    Args:
        storage: Storage backend. If None, creates FileStorage with default settings.
        concurrency: Maximum concurrent tasks
        poll_interval: Poll interval when no work available
        base_retry_delay: Base delay for exponential backoff
        sync: If True, return sync WorkerPool; if False, return AsyncWorkerPool

    Returns:
        Worker pool instance
    """
    if storage is None:
        # Create default file storage with a simple serializer
        from .config import get_settings
        from .serialization import create_serializer

        settings = get_settings()
        serializer = create_serializer(settings.serializer.value)
        storage = FileStorage(base_dir=settings.base_dir, serializer=serializer)

    if sync:
        return WorkerPool(storage, concurrency, poll_interval, base_retry_delay)
    else:
        return AsyncWorkerPool(storage, concurrency, poll_interval, base_retry_delay)
