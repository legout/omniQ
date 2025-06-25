# src/omniq/queue/base.py
"""Base task queue interface for OmniQ."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union, Callable
from datetime import timedelta

from omniq.models.task import Task

class BaseTaskQueue(ABC):
    """Abstract base class for task queues."""
    
    @abstractmethod
    def enqueue(
        self, 
        func: Union[Callable, str], 
        func_args: Optional[Dict[str, Any]] = None, 
        queue_name: Optional[str] = None, 
        run_in: Optional[timedelta] = None, 
        ttl: Optional[timedelta] = None, 
        result_ttl: Optional[timedelta] = None
    ) -> str:
        """
        Enqueue a task.
        
        Args:
            func: Function to execute or function name
            func_args: Function arguments
            queue_name: Queue name
            run_in: Time to wait before execution
            ttl: Time-to-live for the task
            result_ttl: Time-to-live for the result
            
        Returns:
            Task ID
        """
        pass
    
    @abstractmethod
    def dequeue(self, queue_names: Optional[List[str]] = None, limit: int = 1) -> List[Task]:
        """
        Dequeue tasks from queues.
        
        Args:
            queue_names: Queue names to dequeue from
            limit: Maximum number of tasks to dequeue
            
        Returns:
            List of tasks
        """
        pass
    
    @abstractmethod
    def complete(self, task_id: str, queue_name: Optional[str] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            queue_name: Queue name
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def fail(self, task_id: str, queue_name: Optional[str] = None) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            queue_name: Queue name
            
        Returns:
            True if successful
        """
        pass