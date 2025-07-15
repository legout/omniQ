"""
Gevent Pool Worker implementation for OmniQ.

This module provides a gevent pool-based worker that uses gevent.pool.Pool
to execute I/O-bound tasks with high concurrency through cooperative multitasking.
Gevent provides async-compatible execution using greenlets for efficient I/O handling.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import gevent
    from gevent import pool
    from gevent import monkey

try:
    import gevent
    from gevent import pool
    from gevent import monkey
    GEVENT_AVAILABLE = True
except ImportError:
    GEVENT_AVAILABLE = False
    gevent = None
    pool = None
    monkey = None

from .async_worker import AsyncWorker
from ..models.task import Task
from ..models.result import TaskResult
from ..models.event import TaskEvent
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

logger = logging.getLogger(__name__)


def _execute_task_in_gevent_pool(
    task_data: dict,
    function_registry: Dict[str, Callable],
    worker_id: str,
    max_retries: int,
    retry_delay: float,
    task_timeout: Optional[float],
    monkey_patch_applied: bool = False
) -> dict:
    """
    Execute a task in a gevent pool greenlet.
    
    This function is designed to be executed in a gevent pool for I/O-bound
    tasks with cooperative multitasking and high concurrency.
    
    Args:
        task_data: Serialized task data
        function_registry: Registry of available functions
        worker_id: Worker identifier
        max_retries: Maximum retry attempts
        retry_delay: Retry delay
        task_timeout: Task timeout
        monkey_patch_applied: Whether monkey patching was applied
        
    Returns:
        Serialized task result
    """
    import logging
    import time
    import inspect
    import asyncio
    from datetime import datetime, timezone
    
    # Set up logging in greenlet
    logger = logging.getLogger(__name__)
    
    try:
        # Recreate task from data
        from ..models.task import Task
        from ..models.result import TaskResult, ResultStatus
        
        task = Task.from_dict(task_data)
        
        # Get the function to execute
        if task.func not in function_registry:
            raise ValueError(f"Function '{task.func}' not found in registry")
        
        func = function_registry[task.func]
        
        # Create result object
        result = TaskResult(task_id=task.id)
        result.mark_started()
        
        start_time = time.time()
        
        try:
            # Check if function is async
            if inspect.iscoroutinefunction(func):
                # Handle async function - we need to run it in an event loop
                # Since we're in a gevent greenlet, we need to create a new event loop
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # No event loop in current thread, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Execute async function
                if task.args and task.kwargs:
                    coro = func(*task.args, **task.kwargs)
                elif task.args:
                    coro = func(*task.args)
                elif task.kwargs:
                    coro = func(**task.kwargs)
                else:
                    coro = func()
                
                # Run the coroutine
                func_result = loop.run_until_complete(coro)
            else:
                # Handle sync function - execute directly
                if task.args and task.kwargs:
                    func_result = func(*task.args, **task.kwargs)
                elif task.args:
                    func_result = func(*task.args)
                elif task.kwargs:
                    func_result = func(**task.kwargs)
                else:
                    func_result = func()
            
            # Mark as completed
            end_time = time.time()
            result.mark_success(func_result)
            # Set execution time manually since mark_success doesn't accept it
            if result.started_at:
                result.execution_time = end_time - start_time
            
        except Exception as e:
            # Mark as failed
            end_time = time.time()
            result.mark_error(e)
            # Set execution time manually since mark_error doesn't accept it
            if result.started_at:
                result.execution_time = end_time - start_time
        
        return result.to_dict()
    
    except Exception as e:
        # Create error result
        from ..models.result import TaskResult, ResultStatus
        result = TaskResult(task_id=task_data.get('id', 'unknown'))
        result.mark_error(e)
        return result.to_dict()


class GeventPoolWorker:
    """
    Gevent Pool Worker implementation.
    
    This worker uses gevent.pool.Pool to execute I/O-bound tasks
    with high concurrency through cooperative multitasking and greenlets.
    Provides async-compatible execution for efficient I/O handling.
    """
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        task_timeout: Optional[float] = None,
        poll_interval: float = 1.0,
        max_workers: Optional[int] = None,
        monkey_patch: bool = False,
    ):
        """
        Initialize the gevent pool worker.
        
        Args:
            worker_id: Unique identifier for this worker instance
            task_queue: Task queue for dequeuing tasks
            result_storage: Storage for task results
            event_storage: Storage for task events
            function_registry: Registry of available functions
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (seconds)
            task_timeout: Maximum time to execute a task (seconds)
            poll_interval: Time between queue polls (seconds)
            max_workers: Maximum number of greenlets in pool (default: 100)
            monkey_patch: Whether to apply gevent monkey patching
        """
        if not GEVENT_AVAILABLE:
            raise RuntimeError(
                "Gevent is not available. Install it with: pip install 'omniq[gevent]'"
            )
        
        self.max_workers = max_workers or 100
        self.monkey_patch = monkey_patch
        self._pool: Optional[Any] = None
        self._running = False
        self._shutdown_requested = False
        self._active_greenlets: List[Any] = []
        self._monkey_patch_applied = False
        
        # Apply monkey patching if requested
        if self.monkey_patch:
            self._apply_monkey_patch()
        
        # Create async worker for coordination
        self._async_worker = AsyncWorker(
            worker_id=worker_id,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            max_retries=max_retries,
            retry_delay=retry_delay,
            task_timeout=task_timeout,
            poll_interval=poll_interval,
        )
        
        # Store function registry for greenlet execution
        self._function_registry = function_registry or {}
        
        logger.info(f"Gevent pool worker {self.worker_id} initialized with {self.max_workers} greenlets")
    
    def _apply_monkey_patch(self) -> None:
        """
        Apply gevent monkey patching for better async compatibility.
        
        Note: Monkey patching should be done carefully and with clear documentation
        as it modifies the behavior of standard library modules globally.
        """
        if not self._monkey_patch_applied and monkey is not None:
            # Patch socket and select for better I/O performance
            monkey.patch_socket()
            monkey.patch_select()
            # Optionally patch threading for better compatibility
            monkey.patch_thread()
            
            self._monkey_patch_applied = True
            logger.info("Gevent monkey patching applied (socket, select, thread)")
    
    @property
    def worker_id(self) -> str:
        """Get the worker ID."""
        return self._async_worker.worker_id
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task in the gevent pool.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        if self._pool is None:
            raise RuntimeError("Gevent pool worker not started")
        
        # Log task execution start (only if storage is available)
        if self._async_worker.event_storage:
            try:
                await self._async_worker._log_event(
                    TaskEvent.create_executing(
                        task_id=task.id,
                        worker_id=self.worker_id
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to log event: {e}")
        
        try:
            # Execute task directly in the current thread using gevent
            # This avoids the asyncio/gevent thread switching issue
            result_data = await self._execute_task_sync(task)
            
            # Recreate result from data
            from ..models.result import TaskResult
            result = TaskResult.from_dict(result_data)
            
            # Store result if storage is available
            if self._async_worker.result_storage:
                try:
                    await self._async_worker._store_result(result)
                except Exception as e:
                    logger.debug(f"Failed to store result: {e}")
            
            # Log completion or failure (only if storage is available)
            if self._async_worker.event_storage:
                try:
                    if result.is_successful():
                        await self._async_worker._log_event(
                            TaskEvent.create_completed(
                                task_id=task.id,
                                worker_id=self.worker_id,
                                execution_time=result.execution_time
                            )
                        )
                        logger.info(f"Task {task.id} completed successfully in gevent pool worker {self.worker_id}")
                    else:
                        await self._async_worker._log_event(
                            TaskEvent.create_failed(
                                task_id=task.id,
                                worker_id=self.worker_id,
                                error=Exception(result.error or "Unknown error"),
                                traceback_str=result.traceback,
                                execution_time=result.execution_time
                            )
                        )
                        logger.error(f"Task {task.id} failed in gevent pool worker {self.worker_id}: {result.error}")
                except Exception as e:
                    logger.debug(f"Failed to log event: {e}")
            
            return result
        
        except Exception as e:
            # Handle execution error
            from ..models.result import TaskResult, ResultStatus
            result = TaskResult(task_id=task.id)
            result.mark_error(e)
            
            if self._async_worker.result_storage:
                try:
                    await self._async_worker._store_result(result)
                except Exception as store_e:
                    logger.debug(f"Failed to store result: {store_e}")
            
            logger.error(f"Gevent pool execution error for task {task.id}: {e}")
            return result
    
    async def _execute_task_sync(self, task: Task) -> dict:
        """
        Execute a task synchronously using gevent pool.
        
        Args:
            task: The task to execute
            
        Returns:
            Serialized task result
        """
        import concurrent.futures
        import threading
        
        # Create a future to hold the result
        future = concurrent.futures.Future()
        
        def run_in_gevent():
            """Run the task in gevent pool and set the future result."""
            try:
                # Check if pool is available
                if self._pool is None:
                    raise RuntimeError("Gevent pool not initialized")
                
                # Submit task to gevent pool
                greenlet = self._pool.spawn(
                    _execute_task_in_gevent_pool,
                    task.to_dict(),
                    self._function_registry,
                    self.worker_id,
                    self._async_worker.max_retries,
                    self._async_worker.retry_delay,
                    self._async_worker.task_timeout,
                    self._monkey_patch_applied
                )
                
                # Track active greenlet
                self._active_greenlets.append(greenlet)
                
                try:
                    # Wait for greenlet completion
                    result_data = greenlet.get()
                    future.set_result(result_data)
                finally:
                    # Remove greenlet from active list
                    if greenlet in self._active_greenlets:
                        self._active_greenlets.remove(greenlet)
                        
            except Exception as e:
                future.set_exception(e)
        
        # Run the gevent task in a separate thread to avoid asyncio conflicts
        thread = threading.Thread(target=run_in_gevent)
        thread.start()
        
        # Wait for the result using asyncio
        loop = asyncio.get_event_loop()
        result_data = await loop.run_in_executor(None, future.result)
        
        return result_data
    
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the gevent pool worker to process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if not self._async_worker.task_queue:
            raise RuntimeError("Task queue not configured")
        
        if self._running:
            logger.warning(f"Gevent pool worker {self.worker_id} is already running")
            return
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        # Start gevent pool
        if pool is not None:
            self._pool = pool.Pool(self.max_workers)
        else:
            raise RuntimeError("Gevent pool module not available")
        
        logger.info(f"Gevent pool worker {self.worker_id} starting, processing queues: {queues}")
        
        try:
            while self._running and not self._shutdown_requested:
                try:
                    # Process a single task
                    result = await self.process_single_task(queues)
                    
                    if result is None:
                        # No task available, wait before polling again
                        await asyncio.sleep(self._async_worker.poll_interval)
                
                except Exception as e:
                    logger.error(f"Error in gevent pool worker {self.worker_id}: {e}")
                    await asyncio.sleep(self._async_worker.poll_interval)
        
        finally:
            await self._cleanup()
    
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the gevent pool worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping gevent pool worker {self.worker_id} (graceful={graceful})")
        
        if graceful:
            self._shutdown_requested = True
            
            # Wait for active tasks to complete
            if self._active_greenlets:
                logger.info(f"Waiting for {len(self._active_greenlets)} active tasks to complete...")
                active_greenlets = self._active_greenlets.copy()
                
                # Wait for all active greenlets to complete
                for greenlet in active_greenlets:
                    try:
                        # Use asyncio to wait for greenlet completion
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, greenlet.get)
                    except Exception as e:
                        logger.warning(f"Error waiting for task completion: {e}")
        else:
            self._running = False
            self._shutdown_requested = True
        
        await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        
        # Shutdown gevent pool
        if self._pool:
            if self._shutdown_requested:
                # Kill all greenlets gracefully
                self._pool.kill()
            else:
                # Force kill all greenlets
                self._pool.kill()
            self._pool = None
        
        # Clear active greenlets
        self._active_greenlets.clear()
        
        logger.info(f"Gevent pool worker {self.worker_id} stopped")
    
    async def process_single_task(self, queues: Optional[List[str]] = None) -> Optional[TaskResult]:
        """
        Process a single task from the queues.
        
        Args:
            queues: List of queue names to check
            
        Returns:
            Task result if a task was processed, None otherwise
        """
        if not self._async_worker.task_queue:
            raise RuntimeError("Task queue not configured")
        
        queues = queues or ["default"]
        
        # Dequeue a task
        task = await self._async_worker.task_queue.dequeue(queues, timeout=0.1)
        
        if task is None:
            return None
        
        # Log dequeue event (only if storage is available)
        if self._async_worker.event_storage:
            try:
                await self._async_worker._log_event(
                    TaskEvent.create_dequeued(
                        task_id=task.id,
                        queue_name=task.queue_name,
                        worker_id=self.worker_id
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to log event: {e}")
        
        # Execute the task
        result = await self.execute_task(task)
        
        return result
    
    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function in the worker's function registry.
        
        Args:
            name: Function name
            func: Function to register
        """
        self._function_registry[name] = func
        self._async_worker.register_function(name, func)
        logger.debug(f"Function '{name}' registered in gevent pool worker {self.worker_id}")
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker."""
        self._shutdown_requested = True
        self._async_worker.request_shutdown()
    
    def get_active_task_count(self) -> int:
        """Get the number of currently active tasks."""
        return len(self._active_greenlets)
    
    def get_gevent_pool_size(self) -> int:
        """Get the configured gevent pool size."""
        return self.max_workers
    
    def is_monkey_patched(self) -> bool:
        """Check if monkey patching was applied."""
        return self._monkey_patch_applied
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Start gevent pool
        if not self._pool:
            if pool is not None:
                self._pool = pool.Pool(self.max_workers)
                # Set running state for direct task execution
                self._running = True
                logger.debug(f"Gevent pool started for worker {self.worker_id}")
            else:
                raise RuntimeError("Gevent pool module not available")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._running:
            await self.stop(graceful=True)
        elif self._pool:
            # Clean up pool if it was started but worker wasn't running
            self._pool.kill()
            self._pool = None
            logger.debug(f"Gevent pool shut down for worker {self.worker_id}")
    
    def __repr__(self) -> str:
        """String representation of the worker."""
        return f"GeventPoolWorker(worker_id='{self.worker_id}', max_workers={self.max_workers})"