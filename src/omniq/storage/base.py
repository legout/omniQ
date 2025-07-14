"""
OmniQ Storage Base Interfaces

This module defines the abstract base classes for all storage backends in OmniQ.
Following the "Async First, Sync Wrapped" pattern, each interface provides both
asynchronous methods and synchronous wrappers using anyio.run().
"""

import anyio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from uuid import UUID

from ..models import Task, TaskResult, TaskEvent


class BaseTaskQueue(ABC):
    """
    Abstract base class for task queue implementations.
    
    This interface defines the common operations for all task queue backends,
    including enqueue, dequeue, acknowledgment, and context management.
    Both async and sync methods are provided following the "Async First, Sync Wrapped" pattern.
    """
    
    # Async methods (core implementation)
    
    @abstractmethod
    async def enqueue(self, task: Task) -> None:
        """
        Add a task to the queue.
        
        Args:
            task: The task to enqueue
        """
        pass
    
    @abstractmethod
    async def dequeue(self, queue: str = "default", timeout: Optional[float] = None) -> Optional[Task]:
        """
        Retrieve a task from the queue.
        
        Args:
            queue: Queue name to dequeue from
            timeout: Maximum time to wait for a task (None for non-blocking)
            
        Returns:
            Task if available, None if no task available within timeout
        """
        pass
    
    @abstractmethod
    async def ack(self, task_id: UUID) -> None:
        """
        Acknowledge successful task completion.
        
        Args:
            task_id: ID of the task to acknowledge
        """
        pass
    
    @abstractmethod
    async def nack(self, task_id: UUID, requeue: bool = True) -> None:
        """
        Negative acknowledgment - task processing failed.
        
        Args:
            task_id: ID of the task to nack
            requeue: Whether to requeue the task for retry
        """
        pass
    
    @abstractmethod
    async def get_queue_info(self, queue: str = "default") -> Dict[str, Any]:
        """
        Get information about a queue.
        
        Args:
            queue: Queue name
            
        Returns:
            Dictionary containing queue information (size, pending tasks, etc.)
        """
        pass
    
    @abstractmethod
    async def list_queues(self) -> List[str]:
        """
        List all available queues.
        
        Returns:
            List of queue names
        """
        pass
    
    @abstractmethod
    async def purge_queue(self, queue: str = "default") -> int:
        """
        Remove all tasks from a queue.
        
        Args:
            queue: Queue name to purge
            
        Returns:
            Number of tasks purged
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection and cleanup resources."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the queue backend."""
        pass
    
    # Async context manager methods
    
    async def __aenter__(self) -> "BaseTaskQueue":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    # Sync wrapper methods
    
    def enqueue_sync(self, task: Task) -> None:
        """Synchronous wrapper for enqueue."""
        return anyio.run(self.enqueue, task)
    
    def dequeue_sync(self, queue: str = "default", timeout: Optional[float] = None) -> Optional[Task]:
        """Synchronous wrapper for dequeue."""
        return anyio.run(self.dequeue, queue, timeout)
    
    def ack_sync(self, task_id: UUID) -> None:
        """Synchronous wrapper for ack."""
        return anyio.run(self.ack, task_id)
    
    def nack_sync(self, task_id: UUID, requeue: bool = True) -> None:
        """Synchronous wrapper for nack."""
        return anyio.run(self.nack, task_id, requeue)
    
    def get_queue_info_sync(self, queue: str = "default") -> Dict[str, Any]:
        """Synchronous wrapper for get_queue_info."""
        return anyio.run(self.get_queue_info, queue)
    
    def list_queues_sync(self) -> List[str]:
        """Synchronous wrapper for list_queues."""
        return anyio.run(self.list_queues)
    
    def purge_queue_sync(self, queue: str = "default") -> int:
        """Synchronous wrapper for purge_queue."""
        return anyio.run(self.purge_queue, queue)
    
    def close_sync(self) -> None:
        """Synchronous wrapper for close."""
        return anyio.run(self.close)
    
    def connect_sync(self) -> None:
        """Synchronous wrapper for connect."""
        return anyio.run(self.connect)
    
    # Sync context manager methods
    
    def __enter__(self) -> "BaseTaskQueue":
        """Sync context manager entry."""
        anyio.run(self.connect)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        anyio.run(self.close)


class BaseResultStorage(ABC):
    """
    Abstract base class for task result storage implementations.
    
    This interface defines the common operations for storing and retrieving task results.
    Both async and sync methods are provided following the "Async First, Sync Wrapped" pattern.
    """
    
    # Async methods (core implementation)
    
    @abstractmethod
    async def store_result(self, result: TaskResult) -> None:
        """
        Store a task result.
        
        Args:
            result: The task result to store
        """
        pass
    
    @abstractmethod
    async def get_result(self, task_id: UUID) -> Optional[TaskResult]:
        """
        Retrieve a task result by task ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            TaskResult if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_result(self, task_id: UUID) -> bool:
        """
        Delete a task result.
        
        Args:
            task_id: ID of the task whose result to delete
            
        Returns:
            True if result was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_results(self, task_ids: List[UUID]) -> Dict[UUID, TaskResult]:
        """
        Retrieve multiple task results.
        
        Args:
            task_ids: List of task IDs
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_results(self) -> int:
        """
        Remove expired results based on TTL.
        
        Returns:
            Number of expired results removed
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection and cleanup resources."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass
    
    # Async context manager methods
    
    async def __aenter__(self) -> "BaseResultStorage":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    # Sync wrapper methods
    
    def store_result_sync(self, result: TaskResult) -> None:
        """Synchronous wrapper for store_result."""
        return anyio.run(self.store_result, result)
    
    def get_result_sync(self, task_id: UUID) -> Optional[TaskResult]:
        """Synchronous wrapper for get_result."""
        return anyio.run(self.get_result, task_id)
    
    def delete_result_sync(self, task_id: UUID) -> bool:
        """Synchronous wrapper for delete_result."""
        return anyio.run(self.delete_result, task_id)
    
    def get_results_sync(self, task_ids: List[UUID]) -> Dict[UUID, TaskResult]:
        """Synchronous wrapper for get_results."""
        return anyio.run(self.get_results, task_ids)
    
    def cleanup_expired_results_sync(self) -> int:
        """Synchronous wrapper for cleanup_expired_results."""
        return anyio.run(self.cleanup_expired_results)
    
    def close_sync(self) -> None:
        """Synchronous wrapper for close."""
        return anyio.run(self.close)
    
    def connect_sync(self) -> None:
        """Synchronous wrapper for connect."""
        return anyio.run(self.connect)
    
    # Sync context manager methods
    
    def __enter__(self) -> "BaseResultStorage":
        """Sync context manager entry."""
        anyio.run(self.connect)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        anyio.run(self.close)


class BaseEventStorage(ABC):
    """
    Abstract base class for task event storage implementations.
    
    This interface defines the common operations for storing and retrieving task events.
    Both async and sync methods are provided following the "Async First, Sync Wrapped" pattern.
    """
    
    # Async methods (core implementation)
    
    @abstractmethod
    async def log_event(self, event: TaskEvent) -> None:
        """
        Log a task event.
        
        Args:
            event: The task event to log
        """
        pass
    
    @abstractmethod
    async def get_events(self, task_id: UUID, limit: Optional[int] = None) -> List[TaskEvent]:
        """
        Retrieve events for a specific task.
        
        Args:
            task_id: ID of the task
            limit: Maximum number of events to return
            
        Returns:
            List of task events ordered by timestamp
        """
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> List[TaskEvent]:
        """
        Retrieve events by type.
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return
            
        Returns:
            List of task events of the specified type
        """
        pass
    
    @abstractmethod
    async def get_events_by_queue(self, queue: str, limit: Optional[int] = None) -> List[TaskEvent]:
        """
        Retrieve events for a specific queue.
        
        Args:
            queue: Queue name
            limit: Maximum number of events to return
            
        Returns:
            List of task events for the specified queue
        """
        pass
    
    @abstractmethod
    async def cleanup_old_events(self, max_age_seconds: int) -> int:
        """
        Remove old events based on age.
        
        Args:
            max_age_seconds: Maximum age of events to keep
            
        Returns:
            Number of events removed
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection and cleanup resources."""
        pass
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass
    
    # Async context manager methods
    
    async def __aenter__(self) -> "BaseEventStorage":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    # Sync wrapper methods
    
    def log_event_sync(self, event: TaskEvent) -> None:
        """Synchronous wrapper for log_event."""
        return anyio.run(self.log_event, event)
    
    def get_events_sync(self, task_id: UUID, limit: Optional[int] = None) -> List[TaskEvent]:
        """Synchronous wrapper for get_events."""
        return anyio.run(self.get_events, task_id, limit)
    
    def get_events_by_type_sync(self, event_type: str, limit: Optional[int] = None) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_by_type."""
        return anyio.run(self.get_events_by_type, event_type, limit)
    
    def get_events_by_queue_sync(self, queue: str, limit: Optional[int] = None) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_by_queue."""
        return anyio.run(self.get_events_by_queue, queue, limit)
    
    def cleanup_old_events_sync(self, max_age_seconds: int) -> int:
        """Synchronous wrapper for cleanup_old_events."""
        return anyio.run(self.cleanup_old_events, max_age_seconds)
    
    def close_sync(self) -> None:
        """Synchronous wrapper for close."""
        return anyio.run(self.close)
    
    def connect_sync(self) -> None:
        """Synchronous wrapper for connect."""
        return anyio.run(self.connect)
    
    # Sync context manager methods
    
    def __enter__(self) -> "BaseEventStorage":
        """Sync context manager entry."""
        anyio.run(self.connect)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        anyio.run(self.close)