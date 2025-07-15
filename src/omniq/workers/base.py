"""
Base worker interface for OmniQ.

This module defines the abstract base class that all worker implementations
must follow, ensuring consistent interfaces across different worker types.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime
import logging

from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent, EventType
from ..storage.base import BaseTaskQueue, BaseResultStorage, BaseEventStorage
from ..queue_manager import QueueManager

logger = logging.getLogger(__name__)


class WorkerError(Exception):
    """Base exception for worker-related errors."""
    pass


class TaskExecutionError(WorkerError):
    """Exception raised when task execution fails."""
    pass


class FunctionResolutionError(WorkerError):
    """Exception raised when function cannot be resolved."""
    pass


class BaseWorker(ABC):
    """
    Abstract base class for all worker implementations.
    
    This class defines the contract that all worker types must implement,
    providing a consistent interface for task execution across different
    worker backends (async, thread, process, etc.).
    """
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        function_registry: Optional[Dict[str, Callable]] = None,
        queue_manager: Optional[QueueManager] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        task_timeout: Optional[float] = None,
    ):
        """
        Initialize the worker.
        
        Args:
            worker_id: Unique identifier for this worker instance
            task_queue: Task queue for dequeuing tasks
            result_storage: Storage for task results
            event_storage: Storage for task events
            function_registry: Registry of available functions
            queue_manager: Queue manager for advanced queue operations
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (seconds)
            task_timeout: Maximum time to execute a task (seconds)
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.task_queue = task_queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.function_registry = function_registry or {}
        self.queue_manager = queue_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.task_timeout = task_timeout
        self._running = False
        self._shutdown_requested = False
        
        logger.info(f"Worker {self.worker_id} initialized")
    
    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
            
        Raises:
            TaskExecutionError: If task execution fails
            FunctionResolutionError: If function cannot be resolved
        """
        pass
    
    @abstractmethod
    async def start(self, queues: Optional[List[str]] = None) -> None:
        """
        Start the worker to process tasks from queues.
        
        Args:
            queues: List of queue names to process (default: ["default"])
        """
        pass
    
    @abstractmethod
    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the worker.
        
        Args:
            graceful: Whether to finish current tasks before stopping
        """
        pass
    
    @abstractmethod
    async def process_single_task(self, queues: Optional[List[str]] = None) -> Optional[TaskResult]:
        """
        Process a single task from the queues.
        
        Args:
            queues: List of queue names to check
            
        Returns:
            Task result if a task was processed, None otherwise
        """
        pass
    
    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function in the worker's function registry.
        
        Args:
            name: Function name
            func: Function to register
        """
        self.function_registry[name] = func
        logger.debug(f"Function '{name}' registered in worker {self.worker_id}")
    
    def resolve_function(self, func_name: str) -> Callable:
        """
        Resolve a function by name from the registry.
        
        Args:
            func_name: Name of the function to resolve
            
        Returns:
            The resolved function
            
        Raises:
            FunctionResolutionError: If function cannot be found
        """
        if func_name not in self.function_registry:
            raise FunctionResolutionError(f"Function '{func_name}' not found in registry")
        
        return self.function_registry[func_name]
    
    async def _log_event(self, event: TaskEvent) -> None:
        """
        Log an event if event storage is available.
        
        Args:
            event: Event to log
        """
        if self.event_storage:
            try:
                await self.event_storage.log_event(event)
            except Exception as e:
                logger.warning(f"Failed to log event: {e}")
    
    async def _store_result(self, result: TaskResult) -> None:
        """
        Store a task result if result storage is available.
        
        Args:
            result: Result to store
        """
        if self.result_storage:
            try:
                await self.result_storage.set(result)
            except Exception as e:
                logger.warning(f"Failed to store result: {e}")
    
    async def _update_task_status(self, task: Task, status: TaskStatus) -> None:
        """
        Update task status in the queue.
        
        Args:
            task: Task to update
            status: New status
        """
        if self.task_queue:
            try:
                task.status = status
                await self.task_queue.update_task(task)
            except Exception as e:
                logger.warning(f"Failed to update task status: {e}")
    
    async def _dequeue_task(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """
        Dequeue a task using the queue manager if available, otherwise use direct queue access.
        
        Args:
            queues: List of queue names to check
            timeout: Maximum time to wait for a task
            
        Returns:
            Next available task or None
        """
        if self.queue_manager:
            return await self.queue_manager.dequeue_with_routing(queues, timeout)
        elif self.task_queue:
            return await self.task_queue.dequeue(queues, timeout)
        else:
            return None
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown of the worker."""
        self._shutdown_requested = True
        logger.info(f"Shutdown requested for worker {self.worker_id}")
    
    def __repr__(self) -> str:
        """String representation of the worker."""
        return f"{self.__class__.__name__}(worker_id='{self.worker_id}')"