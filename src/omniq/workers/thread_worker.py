"""
Thread worker implementation for OmniQ.

This module provides a thread-based worker that wraps the async worker
to provide synchronous execution in thread pools.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Callable
import logging

from .async_worker import AsyncWorker
from ..models.task import Task
from ..models.result import TaskResult
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage

logger = logging.getLogger(__name__)


class ThreadWorker:
    """
    Thread-based worker implementation.
    
    This worker runs async tasks in a thread pool, providing a synchronous
    interface while leveraging the async worker's core functionality.
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
        max_workers: int = 4,
    ):
        """
        Initialize the thread worker.
        
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
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._running = False
        self._shutdown_requested = False
        
        # Create async worker instance
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
        
        logger.info(f"Thread worker {self.worker_id} initialized with {max_workers} threads")
    
    @property
    def worker_id(self) -> str:
        """Get the worker ID."""
        return self._async_worker.worker_id
    
    def _start_event_loop(self) -> None:
        """Start the event loop in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def _run_async(self, coro):
        """Run an async coroutine in the event loop thread."""
        if not self._loop:
            raise RuntimeError("Event loop not started")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()
    
    def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task synchronously.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        return self._run_async(self._async_worker.execute_task(task))
    
    def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the thread worker to process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        if self._running:
            logger.warning(f"Thread worker {self.worker_id} is already running")
            return
        
        queues = queues or ["default"]
        self._running = True
        self._shutdown_requested = False
        
        # Start event loop in separate thread
        self._loop_thread = threading.Thread(
            target=self._start_event_loop,
            name=f"EventLoop-{self.worker_id}",
            daemon=True
        )
        self._loop_thread.start()
        
        # Wait for loop to be ready
        while self._loop is None:
            threading.Event().wait(0.01)
        
        # Start thread pool executor
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=f"Worker-{self.worker_id}"
        )
        
        logger.info(f"Thread worker {self.worker_id} starting, processing queues: {queues}")
        
        try:
            # Submit worker tasks to thread pool
            futures = []
            for i in range(self.max_workers):
                future = self._executor.submit(self._worker_thread, queues, i)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Worker thread error: {e}")
        
        finally:
            self._cleanup()
    
    def _worker_thread(self, queues: List[str], thread_id: int) -> None:
        """
        Worker thread function that processes tasks.
        
        Args:
            queues: List of queue names to process
            thread_id: Thread identifier
        """
        thread_name = f"{self.worker_id}-{thread_id}"
        logger.debug(f"Worker thread {thread_name} started")
        
        try:
            while self._running and not self._shutdown_requested:
                try:
                    # Process a single task
                    result = self._run_async(
                        self._async_worker.process_single_task(queues)
                    )
                    
                    if result is None:
                        # No task available, wait before polling again
                        threading.Event().wait(self._async_worker.poll_interval)
                
                except Exception as e:
                    logger.error(f"Error in worker thread {thread_name}: {e}")
                    threading.Event().wait(self._async_worker.poll_interval)
        
        finally:
            logger.debug(f"Worker thread {thread_name} stopped")
    
    def stop(self, graceful: bool = True) -> None:
        """
        Stop the thread worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        logger.info(f"Stopping thread worker {self.worker_id} (graceful={graceful})")
        
        if graceful:
            self._shutdown_requested = True
        else:
            self._running = False
            self._shutdown_requested = True
        
        self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        
        # Shutdown thread pool
        if self._executor:
            if self._shutdown_requested:
                self._executor.shutdown(wait=True)
            else:
                self._executor.shutdown(wait=False)
            self._executor = None
        
        # Stop event loop
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        # Wait for loop thread to finish
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5.0)
        
        self._loop = None
        self._loop_thread = None
        
        logger.info(f"Thread worker {self.worker_id} stopped")
    
    def process_single_task(self, queues: Optional[List[str]] = None) -> Optional[TaskResult]:
        """
        Process a single task from the queues synchronously.
        
        Args:
            queues: List of queue names to check
            
        Returns:
            Task result if a task was processed, None otherwise
        """
        return self._run_async(self._async_worker.process_single_task(queues))
    
    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function in the worker's function registry.
        
        Args:
            name: Function name
            func: Function to register
        """
        self._async_worker.register_function(name, func)
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker."""
        self._shutdown_requested = True
        self._async_worker.request_shutdown()
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        if self._running:
            self.stop(graceful=True)
    
    def __repr__(self) -> str:
        """String representation of the worker."""
        return f"ThreadWorker(worker_id='{self.worker_id}', max_workers={self.max_workers})"