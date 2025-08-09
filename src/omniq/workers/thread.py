"""Thread pool worker implementation for OmniQ.

This module provides a synchronous wrapper around the AsyncWorker,
running the async worker in a thread pool to provide a sync interface.
"""

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Optional

import anyio

from .async import AsyncWorker
from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events.base import BaseEventStorage


logger = logging.getLogger(__name__)


class ThreadPoolWorker:
    """Synchronous wrapper around AsyncWorker using thread pool execution.
    
    This worker provides a synchronous interface while internally using
    the AsyncWorker for actual task processing. It runs the async worker's
    event loop in a separate thread.
    """
    
    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_concurrent_tasks: int = 10,
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0
    ):
        """Initialize the thread pool worker.
        
        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_concurrent_tasks: Maximum number of concurrent tasks
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
        """
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        
        self._async_worker: Optional[AsyncWorker] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """Start the worker in a separate thread."""
        if self._running:
            logger.warning(f"ThreadPoolWorker {self.worker_id} is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        logger.info(f"Starting ThreadPoolWorker {self.worker_id}")
        
        # Create and start the worker thread
        self._worker_thread = threading.Thread(
            target=self._run_worker_thread,
            name=f"omniq-worker-{self.worker_id}",
            daemon=True
        )
        self._worker_thread.start()
    
    def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker gracefully.
        
        Args:
            timeout: Maximum time to wait for the worker to stop
        """
        if not self._running:
            return
        
        logger.info(f"Stopping ThreadPoolWorker {self.worker_id}")
        
        # Signal the worker to stop
        self._stop_event.set()
        
        # Wait for the worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
            
            if self._worker_thread.is_alive():
                logger.warning(f"Worker thread did not stop within {timeout} seconds")
        
        self._running = False
        logger.info(f"ThreadPoolWorker {self.worker_id} stopped")
    
    def _run_worker_thread(self) -> None:
        """Run the async worker in a dedicated thread with its own event loop."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            
            # Create the async worker
            self._async_worker = AsyncWorker(
                queue=self.queue,
                result_storage=self.result_storage,
                event_storage=self.event_storage,
                queue_name=self.queue_name,
                worker_id=self.worker_id,
                max_concurrent_tasks=self.max_concurrent_tasks,
                task_timeout=self.task_timeout,
                poll_interval=self.poll_interval
            )
            
            # Run the worker with graceful shutdown handling
            loop.run_until_complete(self._run_with_shutdown())
            
        except Exception as e:
            logger.error(f"Error in worker thread: {e}", exc_info=True)
        finally:
            # Clean up the event loop
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self._loop = None
            self._async_worker = None
    
    async def _run_with_shutdown(self) -> None:
        """Run the async worker with shutdown monitoring."""
        # Start the async worker in the background
        worker_task = asyncio.create_task(self._async_worker.run())
        
        try:
            # Monitor for stop signal
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
            
            # Stop signal received, gracefully stop the worker
            logger.info("Stop signal received, stopping async worker")
            await self._async_worker.stop()
            
        except Exception as e:
            logger.error(f"Error during worker shutdown: {e}", exc_info=True)
        finally:
            # Cancel the worker task if it's still running
            if not worker_task.done():
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
    
    def is_running(self) -> bool:
        """Check if the worker is currently running.
        
        Returns:
            True if the worker is running, False otherwise
        """
        return self._running and (
            self._worker_thread is not None and 
            self._worker_thread.is_alive()
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()