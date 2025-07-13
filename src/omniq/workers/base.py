"""Base worker interfaces and common functionality."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from ..config.loader import LoggingConfig
from ..events.logger import AsyncEventLogger
from ..models.result import TaskResult
from ..models.task import Task
from ..storage.base import BaseTaskQueue


class WorkerState(str, Enum):
    """Worker state enumeration."""
    
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseWorker(ABC):
    """Abstract base class for all worker implementations."""
    
    def __init__(
        self,
        queue: BaseTaskQueue,
        event_logger: Optional[AsyncEventLogger] = None,
        worker_id: Optional[str] = None,
        queues: Optional[List[str]] = None,
        polling_interval: float = 1.0,
        heartbeat_interval: float = 30.0,
        shutdown_timeout: float = 30.0
    ):
        """
        Initialize base worker.
        
        Args:
            queue: Task queue for retrieving tasks
            event_logger: Optional event logger
            worker_id: Unique worker identifier
            queues: List of queue names to process
            polling_interval: Queue polling interval in seconds
            heartbeat_interval: Heartbeat interval in seconds
            shutdown_timeout: Graceful shutdown timeout in seconds
        """
        self.queue = queue
        self.event_logger = event_logger
        self.worker_id = worker_id or str(uuid4())
        self.queues = queues or ["default"]
        self.polling_interval = polling_interval
        self.heartbeat_interval = heartbeat_interval
        self.shutdown_timeout = shutdown_timeout
        
        self._state = WorkerState.IDLE
        self._stop_event = asyncio.Event()
        self._current_task: Optional[Task] = None
        self._start_time: Optional[float] = None
        self._last_heartbeat: Optional[float] = None
        self._tasks_processed = 0
        self._tasks_failed = 0
        self._logger = LoggingConfig.get_logger(f"workers.{self.worker_type}")
    
    @property
    @abstractmethod
    def worker_type(self) -> str:
        """Get worker type identifier."""
        pass
    
    @property
    def state(self) -> WorkerState:
        """Get current worker state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._state == WorkerState.RUNNING
    
    @property
    def current_task(self) -> Optional[Task]:
        """Get currently executing task."""
        return self._current_task
    
    @property
    def uptime(self) -> Optional[float]:
        """Get worker uptime in seconds."""
        if self._start_time is None:
            return None
        return time.time() - self._start_time
    
    @property
    def tasks_processed(self) -> int:
        """Get number of tasks processed."""
        return self._tasks_processed
    
    @property
    def tasks_failed(self) -> int:
        """Get number of tasks that failed."""
        return self._tasks_failed
    
    async def start(self) -> None:
        """Start the worker."""
        if self._state != WorkerState.IDLE:
            raise RuntimeError(f"Cannot start worker in state {self._state}")
        
        self._state = WorkerState.RUNNING
        self._start_time = time.time()
        self._stop_event.clear()
        
        self._logger.info(f"Worker {self.worker_id} starting")
        await self._log_event("WORKER_STARTED")
        
        # Start main processing loop
        await self._run()
    
    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the worker gracefully."""
        if self._state not in (WorkerState.RUNNING, WorkerState.ERROR):
            return
        
        timeout = timeout or self.shutdown_timeout
        self._state = WorkerState.STOPPING
        self._stop_event.set()
        
        self._logger.info(f"Worker {self.worker_id} stopping")
        
        # Wait for current task to complete or timeout
        if self._current_task:
            try:
                await asyncio.wait_for(self._wait_for_current_task(), timeout=timeout)
            except asyncio.TimeoutError:
                self._logger.warning(f"Worker {self.worker_id} shutdown timeout")
        
        self._state = WorkerState.STOPPED
        await self._log_event("WORKER_STOPPED")
        self._logger.info(f"Worker {self.worker_id} stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "state": self._state.value,
            "uptime": self.uptime,
            "current_task": self._current_task.id if self._current_task else None,
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
            "last_heartbeat": self._last_heartbeat,
            "queues": self.queues,
        }
    
    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task and return the result."""
        pass
    
    async def _run(self) -> None:
        """Main worker run loop."""
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Get next task from queue
                    task = await self._get_next_task()
                    
                    if task is None:
                        # No tasks available, wait before polling again
                        await asyncio.sleep(self.polling_interval)
                        continue
                    
                    # Process the task
                    await self._process_task(task)
                    
                except Exception as e:
                    self._logger.error(f"Error in worker run loop: {e}")
                    self._state = WorkerState.ERROR
                    await asyncio.sleep(self.polling_interval)
        
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _get_next_task(self) -> Optional[Task]:
        """Get next task from queue with priority handling."""
        # Try each queue in order (priority is handled by queue implementation)
        for queue_name in self.queues:
            task = await self.queue.dequeue(queue_name, timeout=0.1)
            if task:
                return task
        return None
    
    async def _process_task(self, task: Task) -> None:
        """Process a single task."""
        self._current_task = task
        start_time = time.time()
        
        try:
            # Log task started
            await self._log_event("TASK_STARTED", task.id)
            
            # Execute the task
            result = await self.execute_task(task)
            
            # Update statistics
            self._tasks_processed += 1
            
            # Log task completed
            duration_ms = (time.time() - start_time) * 1000
            await self._log_event("TASK_COMPLETED", task.id, duration_ms=duration_ms)
            
        except Exception as e:
            # Handle task failure
            self._tasks_failed += 1
            duration_ms = (time.time() - start_time) * 1000
            
            # Create failure result
            result = TaskResult.failure(
                task_id=task.id,
                error=e,
                started_at=start_time,
                worker_id=self.worker_id,
                worker_type=self.worker_type
            )
            
            # Log task failed
            await self._log_event("TASK_FAILED", task.id, error=e, duration_ms=duration_ms)
            
        finally:
            self._current_task = None
    
    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat loop."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.heartbeat_interval
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                # Send heartbeat
                self._last_heartbeat = time.time()
                await self._log_event("WORKER_HEARTBEAT")
    
    async def _wait_for_current_task(self) -> None:
        """Wait for current task to complete."""
        while self._current_task is not None:
            await asyncio.sleep(0.1)
    
    async def _log_event(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log worker event."""
        if self.event_logger:
            from ..models.event import TaskEvent, TaskEventType
            
            # Map event types
            event_type_mapping = {
                "WORKER_STARTED": TaskEventType.WORKER_ASSIGNED,
                "WORKER_STOPPED": TaskEventType.WORKER_RELEASED,
                "WORKER_HEARTBEAT": TaskEventType.WORKER_ASSIGNED,  # Use as heartbeat
                "TASK_STARTED": TaskEventType.STARTED,
                "TASK_COMPLETED": TaskEventType.COMPLETED,
                "TASK_FAILED": TaskEventType.FAILED,
            }
            
            mapped_event_type = event_type_mapping.get(event_type)
            if mapped_event_type:
                event = TaskEvent(
                    task_id=task_id or self.worker_id,
                    event_type=mapped_event_type,
                    worker_id=self.worker_id,
                    worker_type=self.worker_type,
                    **kwargs
                )
                await self.event_logger.log_event(event)


def resolve_function(func_path: str) -> Callable:
    """
    Resolve function from string path.
    
    Args:
        func_path: Function path like "module.submodule.function"
    
    Returns:
        Resolved function object
    """
    import importlib
    
    if "." not in func_path:
        raise ValueError(f"Invalid function path: {func_path}")
    
    module_path, func_name = func_path.rsplit(".", 1)
    
    try:
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Cannot resolve function {func_path}: {e}") from e