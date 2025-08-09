"""Gevent pool worker implementation for OmniQ.

This module provides gevent-based worker implementations that can execute
both sync and async tasks, running them in gevent greenlets for efficient
I/O-bound concurrency.
"""

import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Dict

import anyio

try:
    import gevent
    from gevent import monkey, pool, queue as gqueue
    from gevent.event import Event as GeventEvent
    GEVENT_AVAILABLE = True
except ImportError:
    GEVENT_AVAILABLE = False

from .base import BaseWorker
from ..models.task import Task
from ..models.result import TaskResult, TaskStatus
from ..models.event import TaskEvent, TaskEventType
from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events.base import BaseEventStorage


logger = logging.getLogger(__name__)


class AsyncGeventWorker(BaseWorker):
    """Async gevent worker implementation for executing tasks.
    
    This worker uses gevent greenlets to execute tasks, providing efficient
    I/O-bound concurrency. It can handle both sync and async tasks, managing
    the complete task lifecycle including dequeuing, execution, result storage,
    and event logging.
    """
    
    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_greenlets: int = 100,
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0,
        patch_all: bool = True
    ):
        """Initialize the async gevent worker.
        
        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_greenlets: Maximum number of concurrent greenlets
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
            patch_all: Whether to apply gevent monkey patching
        """
        if not GEVENT_AVAILABLE:
            raise ImportError("gevent is required for AsyncGeventWorker. Install with: pip install gevent")
        
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id or f"gevent-worker-{uuid.uuid4().hex[:8]}"
        self.max_greenlets = max_greenlets
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        self.patch_all = patch_all
        
        self._running = False
        self._gevent_pool: Optional[pool.Pool] = None
        self._active_tasks: Dict[uuid.UUID, Any] = {}
        self._task_queue: Optional[gqueue.Queue] = None
        self._stop_event: Optional[GeventEvent] = None
        self._main_greenlet: Optional[gevent.Greenlet] = None
    
    async def start(self) -> None:
        """Start the worker and begin processing tasks."""
        if self._running:
            logger.warning(f"Gevent worker {self.worker_id} is already running")
            return
        
        self._running = True
        logger.info(f"Starting gevent worker {self.worker_id} on queue '{self.queue_name}' with {self.max_greenlets} greenlets")
        
        # Apply gevent monkey patching if requested
        if self.patch_all:
            logger.debug("Applying gevent monkey patching")
            monkey.patch_all()
        
        # Initialize gevent components
        self._gevent_pool = pool.Pool(size=self.max_greenlets)
        self._task_queue = gqueue.Queue()
        self._stop_event = GeventEvent()
        
        # Start the main worker loop in a greenlet
        self._main_greenlet = gevent.spawn(self._run_gevent_loop)
        
        # Start the async task processor
        asyncio.create_task(self._process_tasks_async())
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            return
        
        logger.info(f"Stopping gevent worker {self.worker_id}")
        self._running = False
        
        # Signal the gevent loop to stop
        if self._stop_event:
            self._stop_event.set()
        
        # Wait for the main greenlet to finish
        if self._main_greenlet:
            self._main_greenlet.join(timeout=5.0)
            if not self._main_greenlet.dead:
                logger.warning("Main greenlet did not stop gracefully, killing it")
                self._main_greenlet.kill()
        
        # Shutdown the gevent pool
        if self._gevent_pool:
            self._gevent_pool.kill()
            self._gevent_pool = None
        
        logger.info(f"Gevent worker {self.worker_id} stopped")
    
    async def run(self) -> None:
        """Main worker loop for fetching and executing tasks."""
        # This method is required by BaseWorker but the actual work is done
        # in _run_gevent_loop and _process_tasks_async
        while self._running:
            await asyncio.sleep(self.poll_interval)
    
    def _run_gevent_loop(self) -> None:
        """Run the gevent worker loop for fetching tasks."""
        logger.info(f"Gevent worker {self.worker_id} starting gevent loop")
        
        while not self._stop_event.is_set():
            try:
                # Try to dequeue a task
                task = anyio.to_thread.run_sync(
                    self.queue.dequeue_sync,
                    queue_name=self.queue_name,
                    lock_timeout=self.task_timeout
                )
                
                if task is None:
                    # No tasks available, wait before polling again
                    gevent.sleep(self.poll_interval)
                    continue
                
                # Check if task has expired
                if self._is_task_expired(task):
                    logger.warning(f"Task {task.id} has expired, skipping")
                    anyio.to_thread.run_sync(
                        self._log_event_sync,
                        task.id, TaskEventType.FAILED, "Task expired"
                    )
                    anyio.to_thread.run_sync(
                        self.queue.complete_task_sync, task.id
                    )
                    continue
                
                # Add task to the processing queue
                self._task_queue.put(task)
                
            except Exception as e:
                logger.error(f"Error in gevent worker loop: {e}", exc_info=True)
                gevent.sleep(self.poll_interval)
    
    async def _process_tasks_async(self) -> None:
        """Process tasks from the gevent queue using asyncio."""
        logger.info(f"Gevent worker {self.worker_id} starting async task processor")
        
        while self._running:
            try:
                # Get a task from the gevent queue (with timeout)
                try:
                    task = await asyncio.get_event_loop().run_in_executor(
                        None, self._get_task_from_queue
                    )
                except Exception:
                    # No task available, continue
                    await asyncio.sleep(0.1)
                    continue
                
                if task is None:
                    continue
                
                # Process the task in a greenlet
                greenlet = self._gevent_pool.spawn(self._execute_task_in_greenlet, task)
                self._active_tasks[task.id] = greenlet
                
                # Remove completed tasks from tracking
                greenlet.link(lambda g: self._active_tasks.pop(task.id, None))
                
            except Exception as e:
                logger.error(f"Error in async task processor: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    def _get_task_from_queue(self) -> Optional[Task]:
        """Get a task from the gevent queue with timeout.
        
        Returns:
            The task or None if no task is available
        """
        if not self._task_queue:
            return None
        
        try:
            return self._task_queue.get(timeout=0.1)
        except gqueue.Empty:
            return None
    
    def _execute_task_in_greenlet(self, task: Task) -> None:
        """Execute a task in a gevent greenlet.
        
        Args:
            task: The task to execute
        """
        task_id = task.id
        logger.info(f"Executing task {task_id} in greenlet: {task.func_name}")
        
        # Log task started event
        anyio.to_thread.run_sync(self._log_event_sync, task_id, TaskEventType.STARTED)
        
        try:
            # Get the function to execute
            func = self._resolve_function(task.func_name)
            
            # Execute the function with timeout
            timeout_seconds = None
            if self.task_timeout:
                timeout_seconds = self.task_timeout.total_seconds()
            
            result_data = self._execute_with_gevent(
                func, task.args, task.kwargs, timeout_seconds
            )
            
            # Store successful result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result_data=result_data,
                timestamp=datetime.utcnow(),
                ttl=task.ttl
            )
            anyio.to_thread.run_sync(
                self.result_storage.store_result_sync, result
            )
            
            # Log completion event
            anyio.to_thread.run_sync(self._log_event_sync, task_id, TaskEventType.COMPLETED)
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            
            # Store failure result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                result_data=str(e),
                timestamp=datetime.utcnow(),
                ttl=task.ttl
            )
            anyio.to_thread.run_sync(
                self.result_storage.store_result_sync, result
            )
            
            # Log failure event
            anyio.to_thread.run_sync(
                self._log_event_sync, task_id, TaskEventType.FAILED, str(e)
            )
        
        finally:
            # Mark task as completed in the queue
            try:
                anyio.to_thread.run_sync(
                    self.queue.complete_task_sync, task_id
                )
            except Exception as e:
                logger.error(f"Failed to complete task {task_id} in queue: {e}")
    
    def _execute_with_gevent(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        timeout_seconds: Optional[float] = None
    ) -> Any:
        """Execute a function with gevent, handling both sync and async functions.
        
        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            timeout_seconds: Timeout in seconds (None for no timeout)
            
        Returns:
            The function result
            
        Raises:
            gevent.Timeout: If the function times out
            Exception: Any exception raised by the function
        """
        if inspect.iscoroutinefunction(func):
            # For async functions, we need to run them in an event loop
            def async_wrapper():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(func(*args, **kwargs))
                finally:
                    loop.close()
            
            # Run the wrapper with timeout
            if timeout_seconds:
                return gevent.with_timeout(timeout_seconds, async_wrapper)
            else:
                return async_wrapper()
        else:
            # For sync functions, run directly with timeout
            if timeout_seconds:
                return gevent.with_timeout(timeout_seconds, func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
    
    def _resolve_function(self, func_name: str) -> Callable:
        """Resolve a function name to a callable object.
        
        Args:
            func_name: The function name to resolve
            
        Returns:
            The callable function
            
        Raises:
            ValueError: If the function cannot be resolved
        """
        try:
            # Try to get from builtins first
            import builtins
            if hasattr(builtins, func_name):
                return getattr(builtins, func_name)
            
            # Try to import and resolve module.function notation
            if '.' in func_name:
                module_name, function_name = func_name.rsplit('.', 1)
                module = __import__(module_name, fromlist=[function_name])
                return getattr(module, function_name)
            
            # If no module specified, raise an error
            raise ValueError(f"Cannot resolve function '{func_name}'. Use module.function notation.")
            
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot resolve function '{func_name}': {e}")
    
    def _is_task_expired(self, task: Task) -> bool:
        """Check if a task has expired based on its TTL.
        
        Args:
            task: The task to check
            
        Returns:
            True if the task has expired, False otherwise
        """
        if task.ttl is None:
            return False
        
        expiry_time = task.created_at + task.ttl
        return datetime.utcnow() > expiry_time
    
    def _log_event_sync(
        self,
        task_id: uuid.UUID,
        event_type: TaskEventType,
        message: Optional[str] = None
    ) -> None:
        """Log a task lifecycle event synchronously.
        
        Args:
            task_id: ID of the task
            event_type: Type of event
            message: Optional message for the event
        """
        try:
            event = TaskEvent(
                task_id=task_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                worker_id=self.worker_id
            )
            self.event_storage.log_event_sync(event)
            
            if message:
                logger.info(f"Task {task_id} event {event_type.value}: {message}")
            else:
                logger.info(f"Task {task_id} event {event_type.value}")
                
        except Exception as e:
            logger.error(f"Failed to log event for task {task_id}: {e}")
    
    async def _log_event(
        self,
        task_id: uuid.UUID,
        event_type: TaskEventType,
        message: Optional[str] = None
    ) -> None:
        """Log a task lifecycle event asynchronously.
        
        Args:
            task_id: ID of the task
            event_type: Type of event
            message: Optional message for the event
        """
        await anyio.to_thread.run_sync(
            self._log_event_sync, task_id, event_type, message
        )


class GeventPoolWorker:
    """Synchronous wrapper around AsyncGeventWorker.
    
    This worker provides a synchronous interface while internally using
    the AsyncGeventWorker for actual task processing. It runs the async worker's
    event loop in a separate thread.
    """
    
    def __init__(
        self,
        queue: BaseQueue,
        result_storage: BaseResultStorage,
        event_storage: BaseEventStorage,
        queue_name: str = "default",
        worker_id: Optional[str] = None,
        max_greenlets: int = 100,
        task_timeout: Optional[timedelta] = None,
        poll_interval: float = 1.0,
        patch_all: bool = True
    ):
        """Initialize the gevent pool worker.
        
        Args:
            queue: Task queue to dequeue tasks from
            result_storage: Storage for task results
            event_storage: Storage for task lifecycle events
            queue_name: Name of the queue to process
            worker_id: Unique identifier for this worker instance
            max_greenlets: Maximum number of concurrent greenlets
            task_timeout: Default timeout for task execution
            poll_interval: Interval between queue polls in seconds
            patch_all: Whether to apply gevent monkey patching
        """
        if not GEVENT_AVAILABLE:
            raise ImportError("gevent is required for GeventPoolWorker. Install with: pip install gevent")
        
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.queue_name = queue_name
        self.worker_id = worker_id
        self.max_greenlets = max_greenlets
        self.task_timeout = task_timeout
        self.poll_interval = poll_interval
        self.patch_all = patch_all
        
        self._async_worker: Optional[AsyncGeventWorker] = None
        self._worker_thread: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._stop_event = asyncio.Event()
    
    async def _start_async(self) -> None:
        """Start the async worker in the current event loop."""
        if self._running:
            logger.warning(f"GeventPoolWorker {self.worker_id} is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        logger.info(f"Starting GeventPoolWorker {self.worker_id}")
        
        # Create the async worker
        self._async_worker = AsyncGeventWorker(
            queue=self.queue,
            result_storage=self.result_storage,
            event_storage=self.event_storage,
            queue_name=self.queue_name,
            worker_id=self.worker_id,
            max_greenlets=self.max_greenlets,
            task_timeout=self.task_timeout,
            poll_interval=self.poll_interval,
            patch_all=self.patch_all
        )
        
        # Start the async worker
        await self._async_worker.start()
    
    async def _stop_async(self) -> None:
        """Stop the async worker."""
        if not self._running:
            return
        
        logger.info(f"Stopping GeventPoolWorker {self.worker_id}")
        
        # Stop the async worker
        if self._async_worker:
            await self._async_worker.stop()
            self._async_worker = None
        
        self._running = False
        logger.info(f"GeventPoolWorker {self.worker_id} stopped")
    
    def start(self) -> None:
        """Start the worker in a separate thread."""
        if self._running:
            logger.warning(f"GeventPoolWorker {self.worker_id} is already running")
            return
        
        # Create a new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # Run the async start method
        self._loop.run_until_complete(self._start_async())
        
        # Start the worker loop in a separate task
        self._worker_thread = self._loop.create_task(self._run_worker_loop())
    
    def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker gracefully.
        
        Args:
            timeout: Maximum time to wait for the worker to stop
        """
        if not self._running:
            return
        
        logger.info(f"Stopping GeventPoolWorker {self.worker_id}")
        
        # Signal the worker to stop
        self._stop_event.set()
        
        # Stop the async worker
        if self._loop and self._loop.is_running():
            self._loop.run_until_complete(self._stop_async())
        
        # Close the event loop
        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None
        
        self._running = False
        logger.info(f"GeventPoolWorker {self.worker_id} stopped")
    
    async def _run_worker_loop(self) -> None:
        """Run the worker loop with shutdown monitoring."""
        try:
            # Monitor for stop signal
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)
            
            # Stop signal received
            logger.info("Stop signal received, stopping gevent worker")
            
        except Exception as e:
            logger.error(f"Error in gevent worker loop: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if the worker is currently running.
        
        Returns:
            True if the worker is running, False otherwise
        """
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()