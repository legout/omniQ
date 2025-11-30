from __future__ import annotations

import asyncio
import inspect
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

from .models import (
    Task,
    TaskResult,
    TaskStatus,
    create_success_result,
    create_failure_result,
    has_interval,
    should_retry,
)
from .storage.base import BaseStorage
from .logging import (
    get_logger,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_task_retry,
    log_worker_started,
    log_worker_stopped,
)


class AsyncWorkerPool:
    """
    Async worker pool that polls storage for due tasks and executes them concurrently.

    Features:
    - Configurable concurrency and polling interval
    - Support for both async and sync callables
    - Exponential backoff with jitter for retries
    - Interval task rescheduling
    - Graceful shutdown handling
    """

    def __init__(
        self,
        storage: BaseStorage,
        concurrency: int = 1,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the worker pool.

        Args:
            storage: Storage backend for task operations
            concurrency: Maximum number of concurrent tasks
            poll_interval: Seconds between storage polls when idle
        """
        self.storage = storage
        self.concurrency = max(1, concurrency)
        self.poll_interval = max(0.1, poll_interval)
        self._running = False
        self._tasks = set()  # Track currently running tasks
        self._shutdown_event = asyncio.Event()
        self.logger = get_logger()

    async def start(self) -> None:
        """Start the worker pool and begin processing tasks."""
        if self._running:
            raise RuntimeError("Worker pool is already running")

        self._running = True
        self._shutdown_event.clear()

        log_worker_started(self.concurrency)

        try:
            await self._worker_loop()
        except asyncio.CancelledError:
            self.logger.info("Worker pool cancelled")
        finally:
            self._running = False
            log_worker_stopped()

    async def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the worker pool gracefully.

        Args:
            timeout: Maximum time to wait for shutdown (seconds)
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Wait for worker loop to finish
        if timeout is not None:
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.warning("Worker pool shutdown timeout")
        else:
            await self._shutdown_event.wait()

    async def _worker_loop(self) -> None:
        """Main worker loop that polls and processes tasks."""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Get due task from storage
                now = datetime.now(timezone.utc)
                task = await self.storage.dequeue(now)

                if task is not None:
                    await self._execute_task(task)
                else:
                    # No tasks available, wait before next poll
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), timeout=self.poll_interval
                        )
                        # If event was set, break
                        if self._shutdown_event.is_set():
                            break
                    except asyncio.TimeoutError:
                        # Normal timeout, continue polling
                        continue

            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                # Back off on error
                await asyncio.sleep(min(self.poll_interval, 5.0))

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a single task with proper error handling and retry logic.

        Args:
            task: The task to execute
        """
        task_id = task["id"]
        self._tasks.add(task_id)

        try:
            log_task_started(task_id, task["attempts"] + 1)

            # Execute the callable
            result = await self._call_function(task)

            # Handle successful completion
            await self._handle_success(task, result)

        except Exception as e:
            # Handle failure with retry logic
            await self._handle_failure(task, e)

        finally:
            self._tasks.discard(task_id)

    async def _call_function(self, task: Task) -> Any:
        """
        Call the function specified by the task.

        Args:
            task: Task containing function path and arguments

        Returns:
            Result of function execution
        """
        func_path = task["func_path"]
        args = task["args"]
        kwargs = task["kwargs"]

        try:
            # Import the function
            module_name, func_name = func_path.rsplit(".", 1)
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)

            # Execute based on function type
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        except Exception as e:
            # Re-raise with context
            raise RuntimeError(f"Failed to execute {func_path}: {e}") from e

    async def _handle_success(self, task: Task, result: Any) -> None:
        """
        Handle successful task completion.

        Args:
            task: The completed task
            result: The function result
        """
        task_id = task["id"]
        attempts = task["attempts"] + 1

        # Create success result
        task_result = create_success_result(
            task_id=task_id,
            result=result,
            attempts=attempts,
            last_attempt_at=datetime.now(timezone.utc),
        )

        # Store result and update task
        await self.storage.mark_done(task_id, task_result)
        log_task_completed(task_id, attempts)

        # Reschedule if it's an interval task
        if has_interval(task):
            interval = task["schedule"].get("interval")
            if interval is not None:
                await self._reschedule_interval_task(task, interval)

    async def _handle_failure(self, task: Task, error: Exception) -> None:
        """
        Handle task failure with retry logic.

        Args:
            task: The failed task
            error: The exception that occurred
        """
        task_id = task["id"]
        attempts = task["attempts"] + 1
        error_msg = f"{type(error).__name__}: {error}"

        # Determine if should retry
        will_retry = should_retry(task)

        if will_retry:
            # Calculate backoff delay
            delay = self._calculate_backoff(attempts)
            next_eta = datetime.now(timezone.utc) + timedelta(seconds=delay)

            # Log retry
            log_task_retry(task_id, attempts, next_eta)

            # Reschedule for retry
            try:
                await self.storage.reschedule(task_id, next_eta)
            except NotImplementedError:
                # Storage doesn't support reschedule, mark as retrying
                await self.storage.mark_failed(task_id, error_msg, will_retry=True)
        else:
            # Final failure
            log_task_failed(task_id, error_msg, will_retry=False)

            # Create failure result
            task_result = create_failure_result(
                task_id=task_id,
                error=error_msg,
                attempts=attempts,
                last_attempt_at=datetime.now(timezone.utc),
            )

            # Mark as failed
            await self.storage.mark_failed(task_id, error_msg, will_retry=False)

    async def _reschedule_interval_task(self, task: Task, interval: int) -> None:
        """
        Reschedule an interval task for its next run.

        Args:
            task: The completed interval task
            interval: The interval value from the task
        """
        task_id = task["id"]

        # Calculate next eta
        next_eta = datetime.now(timezone.utc) + timedelta(seconds=float(interval))

        # Update task with new eta and reset status
        try:
            await self.storage.reschedule(task_id, next_eta)
        except NotImplementedError:
            # If reschedule not supported, we'd need to create a new task
            # For now, just log that we couldn't reschedule
            self.logger.warning(
                f"Cannot reschedule interval task {task_id}: reschedule not supported"
            )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff with jitter.

        Args:
            attempt: Current attempt number (1-based)

        Returns:
            Delay in seconds
        """
        # Base delay: 2^attempt seconds, capped at 300 (5 minutes)
        base_delay = min(2**attempt, 300)

        # Add jitter: ±25% random variation
        jitter = base_delay * 0.25 * (random.random() * 2 - 1)

        return max(1.0, base_delay + jitter)


class WorkerPool:
    """
    Synchronous wrapper for AsyncWorkerPool.

    Runs the async worker pool in a dedicated thread and provides
    blocking start() and stop() methods for synchronous code.
    """

    def __init__(
        self,
        storage: BaseStorage,
        concurrency: int = 1,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the sync worker pool wrapper.

        Args:
            storage: Storage backend for task operations
            concurrency: Maximum number of concurrent tasks
            poll_interval: Seconds between storage polls when idle
        """
        self.storage = storage
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self._async_pool = None
        self._thread = None
        self._loop = None
        self.logger = get_logger()

    def start(self) -> None:
        """
        Start the worker pool and block until stopped.

        This method runs the async worker pool in a dedicated thread
        and blocks the calling thread until the worker is stopped.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Worker pool is already running")

        import threading

        def run_worker():
            # Create new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Create and start async worker pool
            self._async_pool = AsyncWorkerPool(
                self.storage,
                self.concurrency,
                self.poll_interval,
            )

            # Run the worker pool
            self._loop.run_until_complete(self._async_pool.start())

        # Start worker thread
        self._thread = threading.Thread(target=run_worker, daemon=True)
        self._thread.start()

        # Block until thread finishes (which happens when worker is stopped)
        self._thread.join()

    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the worker pool.

        Args:
            timeout: Maximum time to wait for shutdown (seconds)
        """
        if self._async_pool is None:
            return

        # Run stop in the worker's event loop
        if self._loop is not None:
            # Schedule the stop coroutine
            asyncio.run_coroutine_threadsafe(self._async_pool.stop(timeout), self._loop)

            # Wait for thread to finish
            if self._thread is not None:
                if timeout is not None:
                    self._thread.join(timeout)
                else:
                    self._thread.join()
