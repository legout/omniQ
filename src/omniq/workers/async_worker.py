"""
Async worker module for OmniQ.

This module implements an asynchronous worker for native async task execution,
suitable for I/O-bound tasks.
"""

import asyncio
import logging
from typing import Any, Optional, Set, Dict
from omniq.workers.base import BaseWorker
from omniq.models.task import Task

logger = logging.getLogger(__name__)

class AsyncWorker(BaseWorker):
    """Asynchronous worker implementation for OmniQ, using native async execution."""
    
    def __init__(self, max_tasks: int = 10, timeout: Optional[float] = None):
        """Initialize the async worker.
        
        Args:
            max_tasks (int): Maximum number of tasks the worker can handle concurrently.
            timeout (Optional[float]): Default timeout for task execution in seconds.
        """
        super().__init__(max_tasks=max_tasks, timeout=timeout)
        self.running = False
        self.active_tasks: Set[asyncio.Task] = set()
        self.task_map: Dict[str, asyncio.Task] = {}
        
    async def start(self) -> None:
        """Start the async worker."""
        if self.running:
            logger.warning("Async worker is already running.")
            return
            
        self.running = True
        logger.info("Async worker started with max_tasks=%d", self.max_tasks)
        
    async def shutdown(self) -> None:
        """Shut down the async worker gracefully, waiting for active tasks to complete."""
        if not self.running:
            logger.warning("Async worker is not running.")
            return
            
        self.running = False
        if self.active_tasks:
            logger.info("Waiting for %d active tasks to complete during shutdown.", len(self.active_tasks))
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        logger.info("Async worker stopped.")
        
    async def execute_task(self, task: Task) -> Any:
        """Execute a task asynchronously and return the result.
        
        Args:
            task (Task): The task to execute.
            
        Returns:
            Any: The result of the task execution.
            
        Raises:
            Exception: If the task execution fails.
        """
        if not self.running:
            raise RuntimeError("Async worker is not running.")
            
        if len(self.active_tasks) >= self.max_tasks:
            raise RuntimeError(f"Async worker at capacity ({self.max_tasks} tasks). Cannot accept more tasks.")
            
        timeout = task.timeout if task.timeout is not None else self.timeout
        coro = self._run_task(task)
        if timeout is not None:
            coro = asyncio.wait_for(coro, timeout=timeout)
            
        async_task = asyncio.create_task(coro)
        self.active_tasks.add(async_task)
        self.task_map[task.id] = async_task
        try:
            result = await async_task
            return result
        finally:
            self.active_tasks.discard(async_task)
            self.task_map.pop(task.id, None)
            
    async def _run_task(self, task: Task) -> Any:
        """Run the task function with provided arguments.
        
        Args:
            task (Task): The task to run.
            
        Returns:
            Any: The result of the task execution.
        """
        func = task.func
        args = task.args
        kwargs = task.kwargs
        
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
