"""Async worker implementation for OmniQ.

This module provides the core async worker implementation that can execute
both sync and async tasks, handle timeouts, and manage task lifecycle events.
"""

import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict

import anyio

from .base import BaseWorker
from ..models.task import Task
from ..models.result import TaskResult, TaskStatus
from ..models.event import TaskEvent, TaskEventType
from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events import BaseEventStorage
from ..queue import RetryManager


logger = logging.getLogger(__name__)


class AsyncWorker(BaseWorker):
    """Async worker implementation for executing tasks.

    This worker can handle both sync and async tasks, running sync tasks
    in a thread pool to avoid blocking the event loop. It manages the
    complete task lifecycle including dequeuing, execution, result storage,
    and event logging.
    """

    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_concurrent_tasks: int = 10,
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0,
        retry_manager: Optional[RetryManager] = None,
    ):
        """Initialize the async worker.

        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_concurrent_tasks: Maximum number of concurrent tasks
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
            retry_manager: Optional retry manager for handling failed tasks
        """
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        self.retry_manager = retry_manager or RetryManager()

        self._running = False
        self._task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._active_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the worker and begin processing tasks."""
        if self._running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self._running = True
        logger.info(f"Starting worker {self.worker_id} on queue '{self.queue_name}'")

        # Start the main worker loop
        await self.run()

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            return

        logger.info(f"Stopping worker {self.worker_id}")
        self._running = False

        # Wait for active tasks to complete
        if self._active_tasks:
            logger.info(
                f"Waiting for {len(self._active_tasks)} active tasks to complete"
            )
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        logger.info(f"Worker {self.worker_id} stopped")

    async def run(self) -> None:
        """Main worker loop for fetching and executing tasks."""
        logger.info(f"Worker {self.worker_id} starting main loop")

        while self._running:
            try:
                # Try to dequeue a task
                task = await self.queue.dequeue_async(
                    queue_name=self.queue_name, lock_timeout=self.task_timeout
                )

                if task is None:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Check if task has expired
                if self._is_task_expired(task):
                    logger.warning(f"Task {task.id} has expired, skipping")
                    await self._log_event(task.id, TaskEventType.FAILED, "Task expired")
                    await self.queue.complete_task_async(task.id)
                    continue

                # Process the task concurrently
                task_coroutine = self._process_task(task)
                async_task = asyncio.create_task(task_coroutine)
                self._active_tasks.add(async_task)

                # Remove completed tasks from tracking
                async_task.add_done_callback(self._active_tasks.discard)

            except Exception as e:
                logger.error(f"Error in worker main loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_task(self, task: Task) -> None:
        """Process a single task with concurrency control.

        Args:
            task: The task to process
        """
        async with self._task_semaphore:
            await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task and handle its lifecycle.

        Args:
            task: The task to execute
        """
        task_id = task.id
        logger.info(f"Executing task {task_id}: {task.func_name}")

        # Check if task should be retried
        retry_info = await self.retry_manager.get_retry_info(task_id)
        if retry_info and retry_info["attempts"] >= retry_info["max_attempts"]:
            # Max retries exceeded, move to dead letter queue
            logger.error(
                f"Task {task_id} exceeded max retries, moving to dead letter queue"
            )
            await self._move_to_dead_letter_queue(task, retry_info)
            return

        # Log task started event
        await self._log_event(task_id, TaskEventType.STARTED)

        try:
            # Get the function to execute
            func = self._resolve_function(task.func_name)

            # Execute the function with timeout
            timeout_seconds = None
            if self.task_timeout:
                timeout_seconds = self.task_timeout.total_seconds()

            result_data = await self._execute_function(
                func, task.args, task.kwargs, timeout_seconds
            )

            # Store successful result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result_data=result_data,
                timestamp=datetime.utcnow(),
                ttl=task.ttl,
            )
            await self.result_storage.store_result_async(result)

            # Clear retry info on success
            await self.retry_manager.clear_retry_info(task_id)

            # Log completion event
            await self._log_event(task_id, TaskEventType.COMPLETED)
            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)

            # Handle retry logic
            should_retry, retry_delay = await self.retry_manager.should_retry(
                task_id, e
            )

            if should_retry:
                # Schedule retry
                logger.info(f"Task {task_id} will be retried in {retry_delay} seconds")
                await self._log_event(
                    task_id, TaskEventType.RETRY, f"Will retry in {retry_delay} seconds"
                )

                # Release task back to queue with delay
                await asyncio.sleep(retry_delay)
                await self.queue.release_task_async(task_id)
            else:
                # Max retries exceeded, move to dead letter queue
                logger.error(
                    f"Task {task_id} exceeded max retries, moving to dead letter queue"
                )
                await self._move_to_dead_letter_queue(
                    task, await self.retry_manager.get_retry_info(task_id)
                )

                # Store failure result
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILURE,
                    result_data=str(e),
                    timestamp=datetime.utcnow(),
                    ttl=task.ttl,
                )
                await self.result_storage.store_result_async(result)

                # Log failure event
                await self._log_event(task_id, TaskEventType.FAILED, str(e))

                # Mark task as completed in the queue
                try:
                    await self.queue.complete_task_async(task_id)
                except Exception as queue_error:
                    logger.error(
                        f"Failed to complete task {task_id} in queue: {queue_error}"
                    )

        finally:
            # Mark task as completed in the queue if not retrying
            if not await self.retry_manager.should_retry(task_id, None)[0]:
                try:
                    await self.queue.complete_task_async(task_id)
                except Exception as e:
                    logger.error(f"Failed to complete task {task_id} in queue: {e}")

    async def _execute_function(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        timeout_seconds: Optional[float] = None,
    ) -> Any:
        """Execute a function (sync or async) with optional timeout.

        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            timeout_seconds: Timeout in seconds (None for no timeout)

        Returns:
            The function result

        Raises:
            asyncio.TimeoutError: If the function times out
            Exception: Any exception raised by the function
        """
        if inspect.iscoroutinefunction(func):
            # Async function - execute directly
            if timeout_seconds:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            else:
                return await func(*args, **kwargs)
        else:
            # Sync function - run in thread pool
            if timeout_seconds:
                with anyio.move_on_after(timeout_seconds) as cancel_scope:
                    result = await anyio.to_thread.run_sync(func, *args, **kwargs)
                    if cancel_scope.cancelled_caught:
                        raise asyncio.TimeoutError("Task execution timed out")
                    return result
            else:
                return await anyio.to_thread.run_sync(func, *args, **kwargs)

    def _resolve_function(self, func_name: str) -> Callable:
        """Resolve a function name to a callable object.

        Args:
            func_name: The function name to resolve

        Returns:
            The callable function

        Raises:
            ValueError: If the function cannot be resolved
        """
        # This is a simplified implementation
        # In a real implementation, you might want to support:
        # - Module.function notation
        # - Registered function registry
        # - Import from string

        # For now, we'll assume the function is available in globals
        # or is a simple built-in function
        try:
            # Try to get from builtins first
            import builtins

            if hasattr(builtins, func_name):
                return getattr(builtins, func_name)

            # Try to import and resolve module.function notation
            if "." in func_name:
                module_name, function_name = func_name.rsplit(".", 1)
                module = __import__(module_name, fromlist=[function_name])
                return getattr(module, function_name)

            # If no module specified, raise an error
            raise ValueError(
                f"Cannot resolve function '{func_name}'. Use module.function notation."
            )

        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot resolve function '{func_name}': {e}")

    def _is_task_expired(self, task: Task) -> bool:
        """Check if a task has expired based on its TTL.

        Args:
            task: The task to check

        Returns:
            True if the task has expired, False otherwise
        """
        if task.ttl is None:
            return False

        expiry_time = task.created_at + task.ttl
        return datetime.utcnow() > expiry_time

    async def _move_to_dead_letter_queue(
        self, task: Task, retry_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Move a failed task to the dead letter queue.

        Args:
            task: The task to move
            retry_info: Optional retry information
        """
        try:
            # Create a dead letter task with additional metadata
            dead_letter_task = Task(
                id=task.id,
                func_name=task.func_name,
                args=task.args,
                kwargs=task.kwargs,
                created_at=task.created_at,
                ttl=task.ttl,
            )

            # Add to dead letter queue
            await self.queue.enqueue_async(dead_letter_task, queue_name="dead_letter")

            # Log dead letter event
            error_message = f"Moved to dead letter queue"
            if retry_info:
                error_message += f" after {retry_info.get('attempts', 0)} attempts"

            await self._log_event(task.id, TaskEventType.FAILED, error_message)
            logger.error(f"Task {task.id} moved to dead letter queue: {error_message}")

        except Exception as e:
            logger.error(f"Failed to move task {task.id} to dead letter queue: {e}")

    async def _log_event(
        self,
        task_id: uuid.UUID,
        event_type: TaskEventType,
        message: Optional[str] = None,
    ) -> None:
        """Log a task lifecycle event.

        Args:
            task_id: ID of the task
            event_type: Type of event
            message: Optional message for the event
        """
        try:
            event = TaskEvent(
                task_id=task_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                worker_id=self.worker_id,
            )
            await self.event_storage.log_event_async(event)

            if message:
                logger.info(f"Task {task_id} event {event_type.value}: {message}")
            else:
                logger.info(f"Task {task_id} event {event_type.value}")

        except Exception as e:
            logger.error(f"Failed to log event for task {task_id}: {e}")
