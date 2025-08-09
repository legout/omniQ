"""Process pool worker implementation for OmniQ.

This module provides process-based worker implementations that can execute
both sync and async tasks, running them in separate processes to bypass
GIL limitations for CPU-bound tasks.
"""

import asyncio
import inspect
import logging
import multiprocessing
import pickle
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed

import anyio

from .base import BaseWorker
from ..models.task import Task
from ..models.result import TaskResult, TaskStatus
from ..models.event import TaskEvent, TaskEventType
from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events.base import BaseEventStorage


logger = logging.getLogger(__name__)


class AsyncProcessWorker(BaseWorker):
    """Async process worker implementation for executing tasks.
    
    This worker uses a process pool to execute tasks in separate processes,
    allowing it to bypass the GIL for CPU-bound tasks. It can handle both
    sync and async tasks, managing the complete task lifecycle including
    dequeuing, execution, result storage, and event logging.
    """
    
    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_processes: int = multiprocessing.cpu_count(),
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0
    ):
        """Initialize the async process worker.
        
        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_processes: Maximum number of processes in the pool
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
        """
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id or f"process-worker-{uuid.uuid4().hex[:8]}"
        self.max_processes = max_processes
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        
        self._running = False
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._active_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        self._task_semaphore = asyncio.Semaphore(max_processes)
    
    async def start(self) -> None:
        """Start the worker and begin processing tasks."""
        if self._running:
            logger.warning(f"Process worker {self.worker_id} is already running")
            return
        
        self._running = True
        logger.info(f"Starting process worker {self.worker_id} on queue '{self.queue_name}' with {self.max_processes} processes")
        
        # Initialize the process pool
        self._process_pool = ProcessPoolExecutor(max_workers=self.max_processes)
        
        # Start the main worker loop
        await self.run()
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            return
        
        logger.info(f"Stopping process worker {self.worker_id}")
        self._running = False
        
        # Wait for active tasks to complete
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active tasks to complete")
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        
        # Shutdown the process pool
        if self._process_pool:
            self._process_pool.shutdown(wait=True)
            self._process_pool = None
        
        logger.info(f"Process worker {self.worker_id} stopped")
    
    async def run(self) -> None:
        """Main worker loop for fetching and executing tasks."""
        logger.info(f"Process worker {self.worker_id} starting main loop")
        
        while self._running:
            try:
                # Try to dequeue a task
                task = await self.queue.dequeue_async(
                    queue_name=self.queue_name,
                    lock_timeout=self.task_timeout
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
                self._active_tasks[task.id] = async_task
                
                # Remove completed tasks from tracking
                async_task.add_done_callback(lambda t: self._active_tasks.pop(task.id, None))
                
            except Exception as e:
                logger.error(f"Error in process worker main loop: {e}", exc_info=True)
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
        logger.info(f"Executing task {task_id} in process: {task.func_name}")
        
        # Log task started event
        await self._log_event(task_id, TaskEventType.STARTED)
        
        try:
            # Get the function to execute
            func = self._resolve_function(task.func_name)
            
            # Execute the function in a separate process
            timeout_seconds = None
            if self.task_timeout:
                timeout_seconds = self.task_timeout.total_seconds()
            
            result_data = await self._execute_in_process(
                func, task.args, task.kwargs, timeout_seconds
            )
            
            # Store successful result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result_data=result_data,
                timestamp=datetime.utcnow(),
                ttl=task.ttl
            )
            await self.result_storage.store_result_async(result)
            
            # Log completion event
            await self._log_event(task_id, TaskEventType.COMPLETED)
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            
            # Store failure result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                result_data=str(e),
                timestamp=datetime.utcnow(),
                ttl=task.ttl
            )
            await self.result_storage.store_result_async(result)
            
            # Log failure event
            await self._log_event(task_id, TaskEventType.FAILED, str(e))
        
        finally:
            # Mark task as completed in the queue
            try:
                await self.queue.complete_task_async(task_id)
            except Exception as e:
                logger.error(f"Failed to complete task {task_id} in queue: {e}")
    
    async def _execute_in_process(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        timeout_seconds: Optional[float] = None
    ) -> Any:
        """Execute a function in a separate process.
        
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
        if not self._process_pool:
            raise RuntimeError("Process pool not initialized")
        
        # Create a pickled representation of the function and arguments
        # This is necessary because functions need to be picklable to be sent to processes
        try:
            # For async functions, we need to run them in an event loop in the process
            if inspect.iscoroutinefunction(func):
                # Create a wrapper that runs the async function in a new event loop
                def async_wrapper():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
                
                # Run the wrapper in the process pool
                future = self._process_pool.submit(async_wrapper)
            else:
                # For sync functions, run directly
                future = self._process_pool.submit(func, *args, **kwargs)
            
            # Wait for the result with timeout
            if timeout_seconds:
                try:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, future.result),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    future.cancel()
                    raise asyncio.TimeoutError("Task execution timed out")
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, future.result)
            
            return result
            
        except Exception as e:
            # Re-raise any exceptions
            raise e
    
    def _resolve_function(self, func_name: str) -> Callable:
        """Resolve a function name to a callable object.
        
        Args:
            func_name: The function name to resolve
            
        Returns:
            The callable function
            
        Raises:
            ValueError: If the function cannot be resolved
        """
        try:
            # Try to get from builtins first
            import builtins
            if hasattr(builtins, func_name):
                return getattr(builtins, func_name)
            
            # Try to import and resolve module.function notation
            if '.' in func_name:
                module_name, function_name = func_name.rsplit('.', 1)
                module = __import__(module_name, fromlist=[function_name])
                return getattr(module, function_name)
            
            # If no module specified, raise an error
            raise ValueError(f"Cannot resolve function '{func_name}'. Use module.function notation.")
            
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
    
    async def _log_event(
        self,
        task_id: uuid.UUID,
        event_type: TaskEventType,
        message: Optional[str] = None
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
                worker_id=self.worker_id
            )
            await self.event_storage.log_event_async(event)
            
            if message:
                logger.info(f"Task {task_id} event {event_type.value}: {message}")
            else:
                logger.info(f"Task {task_id} event {event_type.value}")
                
        except Exception as e:
            logger.error(f"Failed to log event for task {task_id}: {e}")


class ProcessPoolWorker:
    """Synchronous wrapper around AsyncProcessWorker.
    
    This worker provides a synchronous interface while internally using
    the AsyncProcessWorker for actual task processing. It runs the async worker's
    event loop in a separate thread.
    """
    
    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_processes: int = multiprocessing.cpu_count(),
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0
    ):
        """Initialize the process pool worker.
        
        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_processes: Maximum number of processes in the pool
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
        """
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id
        self.max_processes = max_processes
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        
        self._async_worker: Optional[AsyncProcessWorker] = None
        self._worker_thread: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._stop_event = asyncio.Event()
    
    async def _start_async(self) -> None:
        """Start the async worker in the current event loop."""
        if self._running:
            logger.warning(f"ProcessPoolWorker {self.worker_id} is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        logger.info(f"Starting ProcessPoolWorker {self.worker_id}")
        
        # Create the async worker
        self._async_worker = AsyncProcessWorker(
            queue=self.queue,
            result_storage=self.result_storage,
            event_storage=self.event_storage,
            queue_name=self.queue_name,
            worker_id=self.worker_id,
            max_processes=self.max_processes,
            task_timeout=self.task_timeout,
            poll_interval=self.poll_interval
        )
        
        # Start the async worker
        await self._async_worker.start()
    
    async def _stop_async(self) -> None:
        """Stop the async worker."""
        if not self._running:
            return
        
        logger.info(f"Stopping ProcessPoolWorker {self.worker_id}")
        
        # Stop the async worker
        if self._async_worker:
            await self._async_worker.stop()
            self._async_worker = None
        
        self._running = False
        logger.info(f"ProcessPoolWorker {self.worker_id} stopped")
    
    def start(self) -> None:
        """Start the worker in a separate thread."""
        if self._running:
            logger.warning(f"ProcessPoolWorker {self.worker_id} is already running")
            return
        
        # Create a new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # Run the async start method
        self._loop.run_until_complete(self._start_async())
        
        # Start the worker loop in a separate task
        self._worker_thread = self._loop.create_task(self._run_worker_loop())
    
    def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker gracefully.
        
        Args:
            timeout: Maximum time to wait for the worker to stop
        """
        if not self._running:
            return
        
        logger.info(f"Stopping ProcessPoolWorker {self.worker_id}")
        
        # Signal the worker to stop
        self._stop_event.set()
        
        # Stop the async worker
        if self._loop and self._loop.is_running():
            self._loop.run_until_complete(self._stop_async())
        
        # Close the event loop
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None
        
        self._running = False
        logger.info(f"ProcessPoolWorker {self.worker_id} stopped")
    
    async def _run_worker_loop(self) -> None:
        """Run the worker loop with shutdown monitoring."""
        try:
            # Monitor for stop signal
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
            
            # Stop signal received
            logger.info("Stop signal received, stopping process worker")
            
        except Exception as e:
            logger.error(f"Error in process worker loop: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if the worker is currently running.
        
        Returns:
            True if the worker is running, False otherwise
        """
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()