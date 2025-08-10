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
        function_registry: Optional[Dict[str, Callable]] = None,
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
            function_registry: Optional registry of allowed functions (name -> callable)
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
        self.function_registry = function_registry or {}

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
            
            # Create a list of tasks to wait for
            tasks_to_wait = list(self._active_tasks)
            
            # Wait for all tasks to complete with a timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_wait, return_exceptions=True),
                    timeout=30.0  # 30 second timeout for graceful shutdown
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout waiting for tasks to complete, cancelling remaining tasks"
                )
                # Cancel remaining tasks
                for task in tasks_to_wait:
                    if not task.done():
                        task.cancel()
                
                # Wait a bit more for cancelled tasks to finish
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks_to_wait, return_exceptions=True),
                        timeout=10.0  # 10 second timeout for cancellation
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Some tasks did not complete gracefully during shutdown"
                    )

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

                # Remove completed tasks from tracking with proper error handling
                def task_done_callback(task: asyncio.Task) -> None:
                    """Callback to handle task completion and cleanup."""
                    self._active_tasks.discard(task)
                    
                    # Check for exceptions in the task
                    if not task.cancelled() and task.exception():
                        logger.error(f"Task {task.get_name()} failed with exception: {task.exception()}")
                
                async_task.add_done_callback(task_done_callback)

            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Connection error in worker main loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Worker main loop was cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker main loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_task(self, task: Task) -> None:
        """Process a single task with concurrency control.

        Args:
            task: The task to process
        """
        # Use try/finally to ensure semaphore is always released
        try:
            async with self._task_semaphore:
                await self._execute_task(task)
        except asyncio.CancelledError:
            logger.info(f"Task {task.id} processing was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}", exc_info=True)
            raise

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
            try:
                await self.result_storage.store_result_async(result)
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Connection error storing result for task {task_id}: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to store result for task {task_id}: {e}", exc_info=True)
                raise

            # Clear retry info on success
            try:
                await self.retry_manager.clear_retry_info(task_id)
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Connection error clearing retry info for task {task_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to clear retry info for task {task_id}: {e}", exc_info=True)

            # Log completion event
            try:
                await self._log_event(task_id, TaskEventType.COMPLETED)
            except Exception as e:
                logger.error(f"Failed to log completion event for task {task_id}: {e}", exc_info=True)
            logger.info(f"Task {task_id} completed successfully")

        except asyncio.TimeoutError as e:
            logger.error(f"Task {task_id} timed out: {e}", exc_info=True)
            await self._handle_task_failure(task_id, e)

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self._handle_task_failure(task_id, e)

        finally:
            # Mark task as completed in the queue if not retrying
            should_retry, _ = await self.retry_manager.should_retry(task_id, None)
            if not should_retry:
                try:
                    await self.queue.complete_task_async(task_id)
                except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Connection error completing task {task_id} in queue: {e}")
                except Exception as e:
                    logger.error(f"Failed to complete task {task_id} in queue: {e}", exc_info=True)

    async def _handle_task_failure(self, task_id: uuid.UUID, error: Exception) -> None:
        """Handle task failure with retry logic.

        Args:
            task_id: ID of the failed task
            error: The exception that caused the failure
        """
        # Handle retry logic
        should_retry, retry_delay = await self.retry_manager.should_retry(task_id, error)

        if should_retry:
            # Schedule retry with non-blocking delay
            logger.info(f"Task {task_id} will be retried in {retry_delay} seconds")
            await self._log_event(
                task_id, TaskEventType.RETRY, f"Will retry in {retry_delay} seconds"
            )

            # Create a non-blocking retry task
            async def retry_task():
                await asyncio.sleep(retry_delay)
                await self.queue.release_task_async(task_id)

            asyncio.create_task(retry_task())
        else:
            # Max retries exceeded, move to dead letter queue
            logger.error(
                f"Task {task_id} exceeded max retries, moving to dead letter queue"
            )
            
            # Get task info for dead letter queue
            try:
                # Get the task from the queue
                task = await self.queue.get_task_async(task_id)
                if task:
                    retry_info = await self.retry_manager.get_retry_info(task_id)
                    await self._move_to_dead_letter_queue(task, retry_info)
            except Exception as e:
                logger.error(f"Failed to get task {task_id} for dead letter queue: {e}")

            # Store failure result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                result_data=str(error),
                timestamp=datetime.utcnow(),
                ttl=None,  # Don't apply TTL to failure results
            )
            try:
                await self.result_storage.store_result_async(result)
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Connection error storing failure result for task {task_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to store failure result for task {task_id}: {e}", exc_info=True)

            # Log failure event
            try:
                await self._log_event(task_id, TaskEventType.FAILED, str(error))
            except Exception as log_error:
                logger.error(f"Failed to log failure event for task {task_id}: {log_error}", exc_info=True)

            # Mark task as completed in the queue
            try:
                await self.queue.complete_task_async(task_id)
            except (ConnectionError, TimeoutError) as queue_error:
                logger.error(
                    f"Connection error completing task {task_id} in queue: {queue_error}"
                )
            except Exception as queue_error:
                logger.error(
                    f"Failed to complete task {task_id} in queue: {queue_error}",
                    exc_info=True
                )

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
            # Async function - execute directly with timeout
            if timeout_seconds:
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs), timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError("Task execution timed out")
            else:
                return await func(*args, **kwargs)
        else:
            # Sync function - run in thread pool with timeout
            if timeout_seconds:
                try:
                    # Use asyncio.wait_for with anyio.to_thread.run_sync for consistent timeout handling
                    return await asyncio.wait_for(
                        anyio.to_thread.run_sync(func, *args, **kwargs),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError("Task execution timed out")
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
        # Look up the function in the safe registry
        if func_name in self.function_registry:
            return self.function_registry[func_name]
        
        # Function not found in registry
        raise ValueError(
            f"Function '{func_name}' is not registered. "
            "Only explicitly registered functions can be executed."
        )

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

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error moving task {task.id} to dead letter queue: {e}")
        except Exception as e:
            logger.error(f"Failed to move task {task.id} to dead letter queue: {e}", exc_info=True)

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

        except ConnectionError as e:
            logger.error(f"Connection error while logging event for task {task_id}: {e}")
        except TimeoutError as e:
            logger.error(f"Timeout while logging event for task {task_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to log event for task {task_id}: {e}", exc_info=True)
