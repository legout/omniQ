"""Base worker module for OmniQ.

This module defines the base interface for workers in OmniQ. All worker implementations
(async, thread, process, gevent) must inherit from BaseWorker and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from omniq.models.task import Task


class BaseWorker(ABC):
    """Abstract base class for worker implementations in OmniQ."""
    
    def __init__(self, max_tasks: int = 10, timeout: Optional[float] = None):
        """Initialize the base worker.
        
        Args:
            max_tasks (int): Maximum number of tasks the worker can handle concurrently.
            timeout (Optional[float]): Default timeout for task execution in seconds.
        """
        self.max_tasks = max_tasks
        self.timeout = timeout
        self.max_workers = max_tasks  # Alias for compatibility
        
    @abstractmethod
    async def start(self) -> None:
        """Start the worker. Must be implemented by subclasses."""
        pass
        
    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the worker gracefully. Must be implemented by subclasses."""
        pass
        
    @abstractmethod
    async def execute_task(self, task: Task) -> Any:
        """Execute a task and return the result.
        
        Args:
            task (Task): The task to execute.
            
        Returns:
            Any: The result of the task execution.
            
        Raises:
            Exception: If the task execution fails.
        """
        pass
