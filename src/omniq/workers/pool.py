"""
Worker pool module for OmniQ.

This module implements a worker pool for managing multiple workers and distributing tasks.
"""

import logging
from typing import Any, Optional, List, Dict
from omniq.workers.base import BaseWorker
from omniq.models.task import Task

logger = logging.getLogger(__name__)

class WorkerPool:
    """Worker pool for managing multiple workers and distributing tasks."""
    
    def __init__(self, worker_type: str, max_workers: int = 10, timeout: Optional[float] = None):
        """Initialize the worker pool.
        
        Args:
            worker_type (str): Type of worker to use in the pool (async, thread, process, gevent).
            max_workers (int): Maximum number of workers in the pool.
            timeout (Optional[float]): Default timeout for task execution in seconds.
        """
        self.worker_type = worker_type
        self.max_workers = max_workers
        self.timeout = timeout
        self.workers: List[BaseWorker] = []
        self.running = False
        self.task_distribution_index = 0
        
    async def start(self) -> None:
        """Start all workers in the pool."""
        if self.running:
            logger.warning("Worker pool is already running.")
            return
            
        self.running = True
        for i in range(self.max_workers):
            worker = self._create_worker()
            await worker.start()
            self.workers.append(worker)
        logger.info("Worker pool started with %d %s workers.", self.max_workers, self.worker_type)
        
    async def shutdown(self) -> None:
        """Shut down all workers in the pool gracefully."""
        if not self.running:
            logger.warning("Worker pool is not running.")
            return
            
        self.running = False
        for worker in self.workers:
            await worker.shutdown()
        self.workers.clear()
        logger.info("Worker pool stopped.")
        
    async def execute_task(self, task: Task) -> Any:
        """Execute a task by distributing it to an available worker.
        
        Args:
            task (Task): The task to execute.
            
        Returns:
            Any: The result of the task execution.
            
        Raises:
            RuntimeError: If the pool is not running or no workers are available.
        """
        if not self.running:
            raise RuntimeError("Worker pool is not running.")
            
        if not self.workers:
            raise RuntimeError("No workers available in the pool.")
            
        # Simple round-robin distribution
        worker_index = self.task_distribution_index % len(self.workers)
        self.task_distribution_index += 1
        worker = self.workers[worker_index]
        
        try:
            return await worker.execute_task(task)
        except Exception as e:
            logger.error("Task %s failed on worker %d: %s", task.id, worker_index, str(e))
            raise
            
    def _create_worker(self) -> BaseWorker:
        """Create a worker instance based on the worker type.
        
        Returns:
            BaseWorker: A new worker instance.
        """
        from omniq.workers.async_worker import AsyncWorker
        from omniq.workers.thread_worker import ThreadWorker
        from omniq.workers.process_worker import ProcessWorker
        from omniq.workers.gevent_worker import GeventWorker
        
        worker_classes = {
            "async": AsyncWorker,
            "thread": ThreadWorker,
            "process": ProcessWorker,
            "gevent": GeventWorker
        }
        
        worker_class = worker_classes.get(self.worker_type)
        if worker_class is None:
            raise ValueError(f"Unknown worker type: {self.worker_type}")
            
        # For simplicity, each worker handles one task at a time in the pool context
        return worker_class(max_tasks=1, timeout=self.timeout)
    
    @property
    def max_tasks(self) -> int:
        """Get the total maximum tasks the pool can handle.
        
        Returns:
            int: Total maximum tasks across all workers.
        """
        return self.max_workers
