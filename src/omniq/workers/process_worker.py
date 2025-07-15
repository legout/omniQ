"""
Process worker implementation for OmniQ.

This module provides a process-based worker that uses multiprocessing
for CPU-intensive tasks, providing true parallelism.
"""

import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List, Optional, Callable
import logging
import pickle

from .async_worker import AsyncWorker
from ..models.task import Task
from ..models.result import TaskResult
from ..models.event import TaskEvent
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

logger = logging.getLogger(__name__)


def _execute_task_in_process(
    task_data: dict,
    function_registry: Dict[str, Callable],
    worker_id: str,
    max_retries: int,
    retry_delay: float,
    task_timeout: Optional[float]
) -> dict:
    """
    Execute a task in a separate process.
    
    This function is designed to be pickled and executed in a subprocess.
    
    Args:
        task_data: Serialized task data
        function_registry: Registry of available functions
        worker_id: Worker identifier
        max_retries: Maximum retry attempts
        retry_delay: Retry delay
        task_timeout: Task timeout
        
    Returns:
        Serialized task result
    """
    import asyncio
    import logging
    from datetime import datetime
    
    # Set up logging in subprocess
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Recreate task from data
        from ..models.task import Task
        task = Task.from_dict(task_data)
        
        # Create async worker for this process
        async_worker = AsyncWorker(
            worker_id=f"{worker_id}-proc",
            function_registry=function_registry,
            max_retries=max_retries,
            retry_delay=retry_delay,
            task_timeout=task_timeout,
        )
        
        # Execute task in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(async_worker.execute_task(task))
            return result.to_dict()
        finally:
            loop.close()
    
    except Exception as e:
        # Create error result
        from ..models.result import TaskResult, ResultStatus
        result = TaskResult(task_id=task_data['id'])
        result.mark_error(e)
        return result.to_dict()


class ProcessWorker:
    """
    Process-based worker implementation.
    
    This worker uses multiprocessing to execute tasks in separate processes,
    providing true parallelism for CPU-intensive tasks.
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
    ):
        """
        Initialize the process worker.
        
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
            max_workers: Maximum number of worker processes (default: CPU count)
        """
        self.max_workers = max_workers or mp.cpu_count()
        self._executor: Optional[ProcessPoolExecutor] = None
        self._running = False
        self._shutdown_requested = False
        
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
        
        # Filter function registry for picklable functions only
        self._picklable_registry = self._filter_picklable_functions(
            function_registry or {}
        )
        
        logger.info(f"Process worker {self.worker_id} initialized with {self.max_workers} processes")
    
    @property
    def worker_id(self) -> str:
        """Get the worker ID."""
        return self._async_worker.worker_id
    
    def _filter_picklable_functions(self, registry: Dict[str, Callable]) -> Dict[str, Callable]:
        """
        Filter function registry to include only picklable functions.
        
        Args:
            registry: Original function registry
            
        Returns:
            Filtered registry with only picklable functions
        """
        picklable_registry = {}
        
        for name, func in registry.items():
            try:
                # Test if function is picklable
                pickle.dumps(func)
                picklable_registry[name] = func
            except (pickle.PicklingError, TypeError) as e:
                logger.warning(f"Function '{name}' is not picklable and will be skipped: {e}")
        
        return picklable_registry
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task in a separate process.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        if not self._executor:
            raise RuntimeError("Process worker not started")
        
        # Log task execution start
        await self._async_worker._log_event(
            TaskEvent.create_executing(
                task_id=task.id,
                worker_id=self.worker_id
            )
        )
        
        try:
            # Submit task to process pool
            loop = asyncio.get_event_loop()
            result_data = await loop.run_in_executor(
                self._executor,
                _execute_task_in_process,
                task.to_dict(),
                self._picklable_registry,
                self.worker_id,
                self._async_worker.max_retries,
                self._async_worker.retry_delay,
                self._async_worker.task_timeout
            )
            
            # Recreate result from data
            from ..models.result import TaskResult
            result = TaskResult.from_dict(result_data)
            
            # Store result if storage is available
            await self._async_worker._store_result(result)
            
            # Log completion or failure
            if result.is_successful():
                await self._async_worker._log_event(
                    TaskEvent.create_completed(
                        task_id=task.id,
                        worker_id=self.worker_id,
                        execution_time=result.execution_time
                    )
                )
                logger.info(f"Task {task.id} completed successfully in process worker {self.worker_id}")
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
                logger.error(f"Task {task.id} failed in process worker {self.worker_id}: {result.error}")
            
            return result
        
        except Exception as e:
            # Handle execution error
            from ..models.result import TaskResult, ResultStatus
            result = TaskResult(task_id=task.id)
            result.mark_error(e)
            
            await self._async_worker._store_result(result)
            
            logger.error(f"Process execution error for task {task.id}: {e}")
            return result
    
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the process worker to process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if not self._async_worker.task_queue:
            raise RuntimeError("Task queue not configured")
        
        if self._running:
            logger.warning(f"Process worker {self.worker_id} is already running")
            return
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        # Start process pool executor
        self._executor = ProcessPoolExecutor(
            max_workers=self.max_workers,
            mp_context=mp.get_context('spawn')  # Use spawn for better isolation
        )
        
        logger.info(f"Process worker {self.worker_id} starting, processing queues: {queues}")
        
        try:
            while self._running and not self._shutdown_requested:
                try:
                    # Process a single task
                    result = await self.process_single_task(queues)
                    
                    if result is None:
                        # No task available, wait before polling again
                        await asyncio.sleep(self._async_worker.poll_interval)
                
                except Exception as e:
                    logger.error(f"Error in process worker {self.worker_id}: {e}")
                    await asyncio.sleep(self._async_worker.poll_interval)
        
        finally:
            await self._cleanup()
    
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the process worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping process worker {self.worker_id} (graceful={graceful})")
        
        if graceful:
            self._shutdown_requested = True
        else:
            self._running = False
            self._shutdown_requested = True
        
        await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        
        # Shutdown process pool
        if self._executor:
            if self._shutdown_requested:
                self._executor.shutdown(wait=True)
            else:
                self._executor.shutdown(wait=False)
            self._executor = None
        
        logger.info(f"Process worker {self.worker_id} stopped")
    
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
        
        # Log dequeue event
        await self._async_worker._log_event(
            TaskEvent.create_dequeued(
                task_id=task.id,
                queue_name=task.queue_name,
                worker_id=self.worker_id
            )
        )
        
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
        # Test if function is picklable
        try:
            pickle.dumps(func)
            self._picklable_registry[name] = func
            self._async_worker.register_function(name, func)
            logger.debug(f"Function '{name}' registered in process worker {self.worker_id}")
        except (pickle.PicklingError, TypeError) as e:
            logger.warning(f"Cannot register non-picklable function '{name}': {e}")
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker."""
        self._shutdown_requested = True
        self._async_worker.request_shutdown()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._running:
            await self.stop(graceful=True)
    
    def __repr__(self) -> str:
        """String representation of the worker."""
        return f"ProcessWorker(worker_id='{self.worker_id}', max_workers={self.max_workers})"