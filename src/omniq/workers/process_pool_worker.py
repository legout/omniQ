"""
Process Pool Worker implementation for OmniQ.

This module provides a process pool-based worker that uses ProcessPoolExecutor
to execute CPU-bound tasks with configurable process pool size, true parallelism,
and process isolation for fault tolerance.
"""

import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, Future
from typing import Any, Dict, List, Optional, Callable
import logging
import pickle

from .async_worker import AsyncWorker
from ..models.task import Task
from ..models.result import TaskResult
from ..models.event import TaskEvent
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

logger = logging.getLogger(__name__)


def _execute_task_in_process_pool(
    task_data: dict,
    function_registry: Dict[str, Callable],
    worker_id: str,
    max_retries: int,
    retry_delay: float,
    task_timeout: Optional[float]
) -> dict:
    """
    Execute a task in a process pool process.
    
    This function is designed to be executed in a process pool for CPU-bound
    tasks with true parallelism and process isolation.
    
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
    
    # Set up logging in process
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


class ProcessPoolWorker:
    """
    Process Pool Worker implementation.
    
    This worker uses ProcessPoolExecutor to execute CPU-bound tasks
    in a configurable process pool, providing true parallelism and
    process isolation for fault tolerance.
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
        Initialize the process pool worker.
        
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
        self._active_futures: List[Future] = []
        self._futures_lock = asyncio.Lock()
        
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
        
        logger.info(f"Process pool worker {self.worker_id} initialized with {self.max_workers} processes")
    
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
            except (pickle.PicklingError, TypeError, AttributeError) as e:
                logger.warning(f"Function '{name}' is not picklable and will be skipped: {e}")
        
        return picklable_registry
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task in the process pool.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        if not self._executor:
            raise RuntimeError("Process pool worker not started")
        
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
            future = self._executor.submit(
                _execute_task_in_process_pool,
                task.to_dict(),
                self._picklable_registry,
                self.worker_id,
                self._async_worker.max_retries,
                self._async_worker.retry_delay,
                self._async_worker.task_timeout
            )
            
            # Track active future
            async with self._futures_lock:
                self._active_futures.append(future)
            
            try:
                # Wait for task completion
                result_data = await loop.run_in_executor(None, future.result)
                
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
                    logger.info(f"Task {task.id} completed successfully in process pool worker {self.worker_id}")
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
                    logger.error(f"Task {task.id} failed in process pool worker {self.worker_id}: {result.error}")
                
                return result
            
            finally:
                # Remove future from active list
                async with self._futures_lock:
                    if future in self._active_futures:
                        self._active_futures.remove(future)
        
        except Exception as e:
            # Handle execution error
            from ..models.result import TaskResult, ResultStatus
            result = TaskResult(task_id=task.id)
            result.mark_error(e)
            
            await self._async_worker._store_result(result)
            
            logger.error(f"Process pool execution error for task {task.id}: {e}")
            return result
    
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the process pool worker to process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if not self._async_worker.task_queue:
            raise RuntimeError("Task queue not configured")
        
        if self._running:
            logger.warning(f"Process pool worker {self.worker_id} is already running")
            return
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        # Start process pool executor
        self._executor = ProcessPoolExecutor(
            max_workers=self.max_workers,
            mp_context=mp.get_context('spawn')  # Use spawn for better isolation
        )
        
        logger.info(f"Process pool worker {self.worker_id} starting, processing queues: {queues}")
        
        try:
            while self._running and not self._shutdown_requested:
                try:
                    # Process a single task
                    result = await self.process_single_task(queues)
                    
                    if result is None:
                        # No task available, wait before polling again
                        await asyncio.sleep(self._async_worker.poll_interval)
                
                except Exception as e:
                    logger.error(f"Error in process pool worker {self.worker_id}: {e}")
                    await asyncio.sleep(self._async_worker.poll_interval)
        
        finally:
            await self._cleanup()
    
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the process pool worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping process pool worker {self.worker_id} (graceful={graceful})")
        
        if graceful:
            self._shutdown_requested = True
            
            # Wait for active tasks to complete
            if self._active_futures:
                logger.info(f"Waiting for {len(self._active_futures)} active tasks to complete...")
                async with self._futures_lock:
                    active_futures = self._active_futures.copy()
                
                # Wait for all active futures to complete
                for future in active_futures:
                    try:
                        await asyncio.get_event_loop().run_in_executor(None, future.result)
                    except Exception as e:
                        logger.warning(f"Error waiting for task completion: {e}")
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
        
        # Clear active futures
        async with self._futures_lock:
            self._active_futures.clear()
        
        logger.info(f"Process pool worker {self.worker_id} stopped")
    
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
            logger.debug(f"Function '{name}' registered in process pool worker {self.worker_id}")
        except (pickle.PicklingError, TypeError, AttributeError) as e:
            logger.warning(f"Cannot register non-picklable function '{name}': {e}")
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker."""
        self._shutdown_requested = True
        self._async_worker.request_shutdown()
    
    def get_active_task_count(self) -> int:
        """Get the number of currently active tasks."""
        # Note: This is an approximation since we can't use threading.Lock in async context
        return len(self._active_futures)
    
    def get_process_pool_size(self) -> int:
        """Get the configured process pool size."""
        return self.max_workers
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Start process pool executor
        if not self._executor:
            self._executor = ProcessPoolExecutor(
                max_workers=self.max_workers,
                mp_context=mp.get_context('spawn')  # Use spawn for better isolation
            )
            logger.debug(f"Process pool executor started for worker {self.worker_id}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._running:
            await self.stop(graceful=True)
        elif self._executor:
            # Clean up executor if it was started but worker wasn't running
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.debug(f"Process pool executor shut down for worker {self.worker_id}")
    
    def __repr__(self) -> str:
        """String representation of the worker."""
        return f"ProcessPoolWorker(worker_id='{self.worker_id}', max_workers={self.max_workers})"