"""Base queue interface for OmniQ.

This module defines the abstract base class for task queue operations:
- BaseQueue: Interface for task queue operations

All interfaces follow the "Async First, Sync Wrapped" principle.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import timedelta
import uuid

from ..models.task import Task


class BaseQueue(ABC):
    """Abstract base class for task queue operations.
    
    Provides both async and sync methods for enqueuing and dequeuing tasks.
    Includes task locking mechanism to prevent duplicate processing.
    """
    
    @abstractmethod
    async def enqueue_async(self, task: Task, queue_name: str = "default") -> None:
        """Enqueue a task asynchronously.
        
        Args:
            task: The task to enqueue
            queue_name: Name of the queue to add the task to
        """
        pass
    
    @abstractmethod
    async def dequeue_async(self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None) -> Optional[Task]:
        """Dequeue and lock a task asynchronously.
        
        Args:
            queue_name: Name of the queue to dequeue from
            lock_timeout: How long to hold the lock (None for no timeout)
            
        Returns:
            The next available task, or None if queue is empty
        """
        pass
    
    @abstractmethod
    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue.
        
        Args:
            task_id: ID of the task to complete
        """
        pass
    
    @abstractmethod
    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue.
        
        Args:
            task_id: ID of the task to release
        """
        pass
    
    @abstractmethod
    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue.
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Number of pending tasks
        """
        pass
    
    @abstractmethod
    async def list_queues_async(self) -> List[str]:
        """List all available queue names.
        
        Returns:
            List of queue names
        """
        pass
    
    # Sync wrapper methods (to be implemented by concrete classes)
    def enqueue(self, task: Task, queue_name: str = "default") -> None:
        """Synchronous wrapper for enqueue_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def dequeue(self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None) -> Optional[Task]:
        """Synchronous wrapper for dequeue_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def complete_task(self, task_id: uuid.UUID) -> None:
        """Synchronous wrapper for complete_task_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def release_task(self, task_id: uuid.UUID) -> None:
        """Synchronous wrapper for release_task_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_queue_size(self, queue_name: str = "default") -> int:
        """Synchronous wrapper for get_queue_size_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def list_queues(self) -> List[str]:
        """Synchronous wrapper for list_queues_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")