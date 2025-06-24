"""SyncTaskQueue: Synchronous task queue implementation for OmniQ."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable

from omniq.models.task_result import TaskResult
from omniq.queue.async_task_queue import AsyncTaskQueue
from omniq.storage.base import BaseTaskStorage, BaseResultStorage

logger = logging.getLogger(__name__)

class SyncTaskQueue:
    """Synchronous task queue implementation for OmniQ, wrapping AsyncTaskQueue."""
    
    def __init__(
        self,
        task_storage: BaseTaskStorage,
        result_storage: BaseResultStorage,
        worker_type: str = "thread",
        max_workers: int = 5,
        task_timeout: Optional[float] = None,
        task_ttl: Optional[float] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize the sync task queue.
        
        Args:
            task_storage (BaseTaskStorage): Storage backend for tasks.
            result_storage (BaseResultStorage): Storage backend for results.
            worker_type (str): Type of worker to use (async, thread, process, gevent).
            max_workers (int): Maximum number of workers.
            task_timeout (Optional[float]): Default task execution timeout in seconds.
            task_ttl (Optional[float]): Default time-to-live for tasks in seconds.
            retry_attempts (int): Default number of retry attempts for failed tasks.
            retry_delay (float): Default delay between retries in seconds.
        """
        self.async_queue = AsyncTaskQueue(
            task_storage=task_storage,
            result_storage=result_storage,
            worker_type=worker_type,
            max_workers=max_workers,
            task_timeout=task_timeout,
            task_ttl=task_ttl,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay
        )
        self.loop = asyncio.get_event_loop()
        if not self.loop.is_running():
            logger.warning("No running event loop found. Creating a new one for synchronous operations.")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
    def start(self) -> None:
        """Start the task queue and worker pool synchronously."""
        asyncio.run_coroutine_threadsafe(self.async_queue.start(), self.loop).result()
        logger.info("Synchronous task queue started.")
        
    def stop(self) -> None:
        """Stop the task queue and perform graceful shutdown synchronously."""
        asyncio.run_coroutine_threadsafe(self.async_queue.stop(), self.loop).result()
        logger.info("Synchronous task queue stopped.")
        
    def enqueue(
        self,
        func: Callable,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        callbacks: Optional[List[Callable]] = None,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        ttl: Optional[float] = None
    ) -> str:
        """Enqueue a task for execution synchronously.
        
        Args:
            func (callable): The function to execute.
            args (Optional[Tuple]): Positional arguments for the function.
            kwargs (Optional[Dict[str, Any]]): Keyword arguments for the function.
            dependencies (Optional[List[str]]): List of task IDs this task depends on.
            callbacks (Optional[List[callable]]): List of callback functions to execute after task completion.
            task_id (Optional[str]): Custom task ID. If not provided, a UUID will be generated.
            timeout (Optional[float]): Task-specific timeout in seconds.
            ttl (Optional[float]): Task-specific time-to-live in seconds.
            
        Returns:
            str: The ID of the enqueued task.
        """
        return asyncio.run_coroutine_threadsafe(
            self.async_queue.enqueue(
                func=func,
                args=args,
                kwargs=kwargs,
                dependencies=dependencies,
                callbacks=callbacks,
                task_id=task_id,
                timeout=timeout,
                ttl=ttl
            ),
            self.loop
        ).result()
        
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Retrieve the result of a task synchronously.
        
        Args:
            task_id (str): The ID of the task.
            timeout (Optional[float]): Maximum time to wait for the result in seconds.
            
        Returns:
            Optional[TaskResult]: The result of the task if available, None otherwise.
        """
        return asyncio.run_coroutine_threadsafe(
            self.async_queue.get_result(task_id, timeout),
            self.loop
        ).result()
