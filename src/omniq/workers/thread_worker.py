"""
Thread worker module for OmniQ.

This module implements a thread pool worker for executing I/O-bound synchronous tasks.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from omniq.workers.base import BaseWorker
from omniq.models.task import Task

logger = logging.getLogger(__name__)

class ThreadWorker(BaseWorker):
    """Thread pool worker implementation for OmniQ, suitable for I/O-bound synchronous tasks."""
    
    def __init__(self, max_tasks: int = 10, timeout: Optional[float] = None):
        """Initialize the thread pool worker.
        
        Args:
            max_tasks (int): Maximum number of tasks (threads) the worker can handle concurrently.
            timeout (Optional[float]): Default timeout for task execution in seconds.
        """
        super().__init__(max_tasks=max_tasks, timeout=timeout)
        self.running = False
        self.executor: Optional[ThreadPoolExecutor] = None
        self.active_tasks: Set[str] = set()
        self.task_futures: Dict[str, Any] = {}
        
    async def start(self) -> None:
        """Start the thread pool worker."""
        if self.running:
            logger.warning("Thread worker is already running.")
            return
            
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_tasks)
        logger.info("Thread worker started with max_tasks=%d", self.max_tasks)
        
    async def shutdown(self) -> None:
        """Shut down the thread worker gracefully, waiting for active tasks to complete."""
        if not self.running:
            logger.warning("Thread worker is not running.")
            return
            
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
        logger.info("Thread worker stopped.")
        
    async def execute_task(self, task: Task) -> Any:
        """Execute a task using the thread pool and return the result.
        
        Args:
            task (Task): The task to execute.
            
        Returns:
            Any: The result of the task execution.
            
        Raises:
            Exception: If the task execution fails or the worker is not running.
        """
        if not self.running or self.executor is None:
            raise RuntimeError("Thread worker is not running.")
            
        if len(self.active_tasks) >= self.max_tasks:
            raise RuntimeError(f"Thread worker at capacity ({self.max_tasks} tasks). Cannot accept more tasks.")
            
        timeout = task.timeout if task.timeout is not None else self.timeout
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(self.executor, self._run_task, task)
        self.active_tasks.add(task.id)
        self.task_futures[task.id] = future
        
        try:
            if timeout is not None:
                result = await asyncio.wait_for(future, timeout=timeout)
            else:
                result = await future
            return result
        finally:
            self.active_tasks.discard(task.id)
            self.task_futures.pop(task.id, None)
            
    def _run_task(self, task: Task) -> Any:
        """Run the task function with provided arguments in a thread.
        
        Args:
            task (Task): The task to run.
            
        Returns:
            Any: The result of the task execution.
        """
        func = task.func
        args = task.args
        kwargs = task.kwargs
        return func(*args, **kwargs)
