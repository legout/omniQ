"""
Gevent worker module for OmniQ.

This module implements a gevent pool worker for high-concurrency workloads using cooperative multitasking.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List
import gevent
from gevent import Greenlet
from gevent.pool import Pool
from omniq.workers.base import BaseWorker
from omniq.models.task import Task

logger = logging.getLogger(__name__)

class GeventWorker(BaseWorker):
    """Gevent pool worker implementation for OmniQ, suitable for high-concurrency workloads."""
    
    def __init__(self, max_tasks: int = 100, timeout: Optional[float] = None):
        """Initialize the gevent pool worker.
        
        Args:
            max_tasks (int): Maximum number of tasks (greenlets) the worker can handle concurrently.
            timeout (Optional[float]): Default timeout for task execution in seconds.
        """
        super().__init__(max_tasks=max_tasks, timeout=timeout)
        self.running = False
        self.pool: Optional[Pool] = None
        self.active_tasks: Dict[str, Greenlet] = {}
        
    async def start(self) -> None:
        """Start the gevent pool worker."""
        if self.running:
            logger.warning("Gevent worker is already running.")
            return
            
        self.running = True
        self.pool = Pool(size=self.max_tasks)
        logger.info("Gevent worker started with max_tasks=%d", self.max_tasks)
        
    async def shutdown(self) -> None:
        """Shut down the gevent worker gracefully, waiting for active tasks to complete."""
        if not self.running:
            logger.warning("Gevent worker is not running.")
            return
            
        self.running = False
        if self.pool:
            self.pool.join()
            self.pool = None
        logger.info("Gevent worker stopped.")
        
    async def execute_task(self, task: Task) -> Any:
        """Execute a task using the gevent pool and return the result.
        
        Args:
            task (Task): The task to execute.
            
        Returns:
            Any: The result of the task execution.
            
        Raises:
            Exception: If the task execution fails or the worker is not running.
        """
        if not self.running or self.pool is None:
            raise RuntimeError("Gevent worker is not running.")
            
        if len(self.active_tasks) >= self.max_tasks:
            raise RuntimeError(f"Gevent worker at capacity ({self.max_tasks} tasks). Cannot accept more tasks.")
            
        timeout = task.timeout if task.timeout is not None else self.timeout
        greenlet = self.pool.spawn(self._run_task, task)
        self.active_tasks[task.id] = greenlet
        
        try:
            if timeout is not None:
                greenlet.join(timeout=timeout)
                if not greenlet.ready():
                    greenlet.kill()
                    raise TimeoutError(f"Task {task.id} timed out after {timeout} seconds.")
            else:
                greenlet.join()
                
            if greenlet.successful():
                return greenlet.value
            else:
                exc = greenlet.exception
                if exc is not None:
                    raise exc
                else:
                    raise RuntimeError(f"Task {task.id} failed without an exception.")
        finally:
            self.active_tasks.pop(task.id, None)
            
    def _run_task(self, task: Task) -> Any:
        """Run the task function with provided arguments in a greenlet.
        
        Args:
            task (Task): The task to run.
            
        Returns:
            Any: The result of the task execution.
        """
        func = task.func
        args = task.args
        kwargs = task.kwargs
        return func(*args, **kwargs)
