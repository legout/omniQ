"""
Worker pool implementation for OmniQ.

This module provides a worker pool that can manage multiple workers
of different types for scalable task processing.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import logging

from .base import BaseWorker
from .async_worker import AsyncWorker
from .thread_worker import ThreadWorker
from .thread_pool_worker import ThreadPoolWorker
from .process_worker import ProcessWorker
from .process_pool_worker import ProcessPoolWorker
from .gevent_pool_worker import GeventPoolWorker
from ..models.task import Task
from ..models.result import TaskResult
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

logger = logging.getLogger(__name__)


class WorkerType(str, Enum):
    """Available worker types."""
    ASYNC = "async"
    THREAD = "thread"
    THREAD_POOL = "thread_pool"
    PROCESS = "process"
    PROCESS_POOL = "process_pool"
    GEVENT_POOL = "gevent_pool"


class WorkerPool:
    """
    Worker pool for managing multiple workers.
    
    This class provides a unified interface for managing multiple workers
    of different types, allowing for scalable task processing.
    """
    
    def __init__(
        self,
        worker_type: WorkerType = WorkerType.ASYNC,
        max_workers: int = 4,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        task_timeout: Optional[float] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the worker pool.
        
        Args:
            worker_type: Type of workers to create
            max_workers: Maximum number of workers
            task_queue: Task queue for dequeuing tasks
            result_storage: Storage for task results
            event_storage: Storage for task events
            function_registry: Registry of available functions
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (seconds)
            task_timeout: Maximum time to execute a task (seconds)
            poll_interval: Time between queue polls (seconds)
        """
        self.worker_type = worker_type
        self.max_workers = max_workers
        self.task_queue = task_queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.function_registry = function_registry or {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        
        self._workers: List[Union[AsyncWorker, ThreadWorker, ThreadPoolWorker, ProcessWorker, ProcessPoolWorker, GeventPoolWorker]] = []
        self._running = False
        self._shutdown_requested = False
        
        logger.info(f"Worker pool initialized with {max_workers} {worker_type} workers")
    
    def _create_worker(self, worker_id: str) -> Union[AsyncWorker, ThreadWorker, ThreadPoolWorker, ProcessWorker, ProcessPoolWorker, GeventPoolWorker]:
        """
        Create a worker of the specified type.
        
        Args:
            worker_id: Unique identifier for the worker
            
        Returns:
            Worker instance
        """
        common_args = {
            "worker_id": worker_id,
            "task_queue": self.task_queue,
            "result_storage": self.result_storage,
            "event_storage": self.event_storage,
            "function_registry": self.function_registry,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "task_timeout": self.task_timeout,
            "poll_interval": self.poll_interval,
        }
        
        if self.worker_type == WorkerType.ASYNC:
            return AsyncWorker(**common_args)
        elif self.worker_type == WorkerType.THREAD:
            return ThreadWorker(**common_args, max_workers=1)  # Single thread per worker
        elif self.worker_type == WorkerType.THREAD_POOL:
            return ThreadPoolWorker(**common_args, max_workers=self.max_workers)  # Configurable thread pool
        elif self.worker_type == WorkerType.PROCESS:
            return ProcessWorker(**common_args, max_workers=1)  # Single process per worker
        elif self.worker_type == WorkerType.PROCESS_POOL:
            return ProcessPoolWorker(**common_args, max_workers=self.max_workers)  # Configurable process pool
        elif self.worker_type == WorkerType.GEVENT_POOL:
            return GeventPoolWorker(**common_args, max_workers=self.max_workers)  # Configurable gevent pool
        else:
            raise ValueError(f"Unsupported worker type: {self.worker_type}")
    
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the worker pool.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if self._running:
            logger.warning("Worker pool is already running")
            return
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        # Create workers
        for i in range(self.max_workers):
            worker_id = f"pool-worker-{i}"
            worker = self._create_worker(worker_id)
            self._workers.append(worker)
        
        logger.info(f"Starting worker pool with {len(self._workers)} workers")
        
        try:
            # Start all workers based on worker type
            if self.worker_type == WorkerType.ASYNC:
                # Start async workers concurrently
                async_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = worker.start(queues)
                        async_tasks.append(task)
                
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
            
            elif self.worker_type == WorkerType.PROCESS:
                # Process workers have async start method
                async_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = worker.start(queues)
                        async_tasks.append(task)
                
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
            
            elif self.worker_type == WorkerType.THREAD:
                # Thread workers have sync start method, run in executor
                loop = asyncio.get_event_loop()
                executor_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = loop.run_in_executor(None, lambda w=worker: w.start(queues))
                        executor_tasks.append(task)
                
                if executor_tasks:
                    await asyncio.gather(*executor_tasks, return_exceptions=True)
            
            elif self.worker_type == WorkerType.THREAD_POOL:
                # Thread pool workers have async start method
                async_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = worker.start(queues)
                        async_tasks.append(task)
                
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
            
            elif self.worker_type == WorkerType.PROCESS_POOL:
                # Process pool workers have async start method
                async_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = worker.start(queues)
                        async_tasks.append(task)
                
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
            
            elif self.worker_type == WorkerType.GEVENT_POOL:
                # Gevent pool workers have async start method
                async_tasks = []
                for worker in self._workers:
                    if hasattr(worker, 'start'):
                        task = worker.start(queues)
                        async_tasks.append(task)
                
                if async_tasks:
                    await asyncio.gather(*async_tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Error in worker pool: {e}")
        
        finally:
            await self._cleanup()
    
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the worker pool.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping worker pool (graceful={graceful})")
        
        if graceful:
            self._shutdown_requested = True
        else:
            self._running = False
            self._shutdown_requested = True
        
        # Stop all workers
        stop_tasks = []
        for worker in self._workers:
            if hasattr(worker, 'stop'):
                if asyncio.iscoroutinefunction(worker.stop):
                    stop_tasks.append(worker.stop(graceful))
                else:
                    # For sync workers
                    loop = asyncio.get_event_loop()
                    stop_tasks.append(loop.run_in_executor(None, worker.stop, graceful))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        self._workers.clear()
        logger.info("Worker pool stopped")
    
    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function in all workers' function registries.
        
        Args:
            name: Function name
            func: Function to register
        """
        self.function_registry[name] = func
        
        # Register in existing workers
        for worker in self._workers:
            if hasattr(worker, 'register_function'):
                worker.register_function(name, func)
        
        logger.debug(f"Function '{name}' registered in worker pool")
    
    def is_running(self) -> bool:
        """Check if the worker pool is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker pool."""
        self._shutdown_requested = True
        
        # Request shutdown for all workers
        for worker in self._workers:
            if hasattr(worker, 'request_shutdown'):
                worker.request_shutdown()
    
    def get_worker_count(self) -> int:
        """Get the number of workers in the pool."""
        return len(self._workers)
    
    def get_running_workers(self) -> int:
        """Get the number of currently running workers."""
        count = 0
        for worker in self._workers:
            if hasattr(worker, 'is_running') and worker.is_running():
                count += 1
        return count
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._running:
            await self.stop(graceful=True)
    
    def __repr__(self) -> str:
        """String representation of the worker pool."""
        return f"WorkerPool(type={self.worker_type}, max_workers={self.max_workers})"