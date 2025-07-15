"""
Async worker implementation for OmniQ.

This module provides the core async worker that handles task execution,
function resolution, error handling, retry logic, and result storage.
"""

import asyncio
import inspect
import traceback
import dill
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
import logging

from .base import BaseWorker, TaskExecutionError, FunctionResolutionError
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent, EventType
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage
from ..queue_manager import QueueManager

logger = logging.getLogger(__name__)


class AsyncWorker(BaseWorker):
    """
    Async worker implementation for executing tasks.
    
    This is the core worker implementation that provides:
    - Task execution engine for both sync and async functions
    - Function resolution and invocation
    - Error handling and retry logic
    - Result capture and storage
    """
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
        queue_manager: Optional[QueueManager] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        task_timeout: Optional[float] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the async worker.
        
        Args:
            worker_id: Unique identifier for this worker instance
            task_queue: Task queue for dequeuing tasks
            result_storage: Storage for task results
            event_storage: Storage for task events
            function_registry: Registry of available functions
            queue_manager: Queue manager for advanced queue operations
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (seconds)
            task_timeout: Maximum time to execute a task (seconds)
            poll_interval: Time between queue polls (seconds)
        """
        super().__init__(
            worker_id=worker_id,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            function_registry=function_registry,
            queue_manager=queue_manager,
            max_retries=max_retries,
            retry_delay=retry_delay,
            task_timeout=task_timeout,
        )
        self.poll_interval = poll_interval
        self._current_task: Optional[Task] = None
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task with comprehensive error handling and retry logic.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        self._current_task = task
        result = TaskResult(task_id=task.id)
        
        try:
            # Log task execution start
            await self._log_event(TaskEvent.create_executing(
                task_id=task.id,
                worker_id=self.worker_id
            ))
            
            # Update task status to running
            await self._update_task_status(task, TaskStatus.RUNNING)
            
            # Mark result as started
            result.mark_started(worker_id=self.worker_id)
            
            # Execute the task with timeout
            task_result = await self._execute_with_timeout(task)
            
            # Mark result as successful
            result.mark_success(task_result)
            
            # Update task status to completed
            await self._update_task_status(task, TaskStatus.COMPLETED)
            
            # Log completion event
            await self._log_event(TaskEvent.create_completed(
                task_id=task.id,
                worker_id=self.worker_id,
                execution_time=result.execution_time
            ))
            
            logger.info(f"Task {task.id} completed successfully by worker {self.worker_id}")
            
        except Exception as e:
            # Handle task execution error
            await self._handle_task_error(task, result, e)
        
        finally:
            # Store the result
            await self._store_result(result)
            self._current_task = None
        
        return result
    
    async def _execute_with_timeout(self, task: Task) -> Any:
        """
        Execute task function with timeout handling.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
            
        Raises:
            TaskExecutionError: If execution fails or times out
        """
        try:
            # Resolve the function
            func = self._resolve_task_function(task)
            
            # Prepare arguments
            args = task.args
            kwargs = task.kwargs
            
            # Execute with timeout if specified
            if self.task_timeout:
                return await asyncio.wait_for(
                    self._invoke_function(func, args, kwargs),
                    timeout=self.task_timeout
                )
            else:
                return await self._invoke_function(func, args, kwargs)
                
        except asyncio.TimeoutError:
            raise TaskExecutionError(f"Task {task.id} timed out after {self.task_timeout} seconds")
        except Exception as e:
            raise TaskExecutionError(f"Task {task.id} execution failed: {e}") from e
    
    def _resolve_task_function(self, task: Task) -> Callable:
        """
        Resolve the function to execute for a task.
        
        Args:
            task: Task containing function information
            
        Returns:
            Resolved function
            
        Raises:
            FunctionResolutionError: If function cannot be resolved
        """
        try:
            # First try to resolve from registry
            return self.resolve_function(task.func)
        except FunctionResolutionError:
            # Try to deserialize function if it's serialized
            try:
                if isinstance(task.func, str) and task.func.startswith('dill:'):
                    # Deserialize dill-encoded function
                    serialized_func = task.func[5:]  # Remove 'dill:' prefix
                    import base64
                    func_bytes = base64.b64decode(serialized_func)
                    return dill.loads(func_bytes)
                else:
                    # Try to import the function
                    return self._import_function(task.func)
            except Exception as e:
                raise FunctionResolutionError(
                    f"Cannot resolve function '{task.func}': {e}"
                ) from e
    
    def _import_function(self, func_name: str) -> Callable:
        """
        Import a function by its dotted name.
        
        Args:
            func_name: Dotted function name (e.g., 'module.function')
            
        Returns:
            Imported function
            
        Raises:
            FunctionResolutionError: If function cannot be imported
        """
        try:
            if '.' not in func_name:
                # Try to get from builtins
                import builtins
                if hasattr(builtins, func_name):
                    return getattr(builtins, func_name)
                else:
                    raise FunctionResolutionError(f"Function '{func_name}' not found")
            
            module_name, function_name = func_name.rsplit('.', 1)
            module = __import__(module_name, fromlist=[function_name])
            return getattr(module, function_name)
        except Exception as e:
            raise FunctionResolutionError(
                f"Cannot import function '{func_name}': {e}"
            ) from e
    
    async def _invoke_function(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """
        Invoke a function, handling both sync and async functions.
        
        Args:
            func: Function to invoke
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Function result
        """
        if inspect.iscoroutinefunction(func):
            # Async function - await directly
            return await func(*args, **kwargs)
        else:
            # Sync function - run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    async def _handle_task_error(self, task: Task, result: TaskResult, error: Exception) -> None:
        """
        Handle task execution error with retry logic.
        
        Args:
            task: Failed task
            result: Task result to update
            error: Exception that occurred
        """
        # Get traceback
        tb_str = traceback.format_exc()
        
        # Mark result as error
        result.mark_error(error, tb_str)
        
        # Log failure event
        await self._log_event(TaskEvent.create_failed(
            task_id=task.id,
            worker_id=self.worker_id,
            error=error,
            traceback_str=tb_str,
            execution_time=result.execution_time
        ))
        
        # Check if task should be retried
        if task.should_retry():
            await self._schedule_retry(task)
        else:
            # Update task status to failed
            await self._update_task_status(task, TaskStatus.FAILED)
            logger.error(f"Task {task.id} failed permanently: {error}")
    
    async def _schedule_retry(self, task: Task) -> None:
        """
        Schedule a task for retry.
        
        Args:
            task: Task to retry
        """
        task.retry_count += 1
        task.status = TaskStatus.PENDING
        task.run_at = task.get_next_retry_time()
        
        # Update task in queue
        await self._update_task_status(task, TaskStatus.PENDING)
        
        # Log retry event
        await self._log_event(TaskEvent.create_retry(
            task_id=task.id,
            retry_count=task.retry_count,
            max_retries=task.max_retries
        ))
        
        logger.info(f"Task {task.id} scheduled for retry {task.retry_count}/{task.max_retries}")
    
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the worker to continuously process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if not self.task_queue:
            raise RuntimeError("Task queue not configured")
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        logger.info(f"Worker {self.worker_id} starting, processing queues: {queues}")
        
        try:
            while self._running and not self._shutdown_requested:
                try:
                    # Process a single task
                    result = await self.process_single_task(queues)
                    
                    if result is None:
                        # No task available, wait before polling again
                        await asyncio.sleep(self.poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error in worker {self.worker_id}: {e}")
                    await asyncio.sleep(self.poll_interval)
        
        finally:
            self._running = False
            logger.info(f"Worker {self.worker_id} stopped")
    
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping worker {self.worker_id} (graceful={graceful})")
        
        if graceful:
            self.request_shutdown()
            # Wait for current task to complete
            while self._current_task is not None:
                await asyncio.sleep(0.1)
        else:
            self._running = False
            self._shutdown_requested = True
    
    async def process_single_task(self, queues: Optional[List[str]] = None) -> Optional[TaskResult]:
        """
        Process a single task from the queues.
        
        Args:
            queues: List of queue names to check
            
        Returns:
            Task result if a task was processed, None otherwise
        """
        if not self.task_queue:
            raise RuntimeError("Task queue not configured")
        
        queues = queues or ["default"]
        
        # Dequeue a task using queue manager if available
        task = await self._dequeue_task(queues, timeout=0.1)
        
        if task is None:
            return None
        
        # Log dequeue event
        await self._log_event(TaskEvent.create_dequeued(
            task_id=task.id,
            queue_name=task.queue_name,
            worker_id=self.worker_id
        ))
        
        # Execute the task
        result = await self.execute_task(task)
        
        return result
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._running:
            await self.stop(graceful=True)