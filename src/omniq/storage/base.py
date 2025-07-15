"""
Base storage interfaces for OmniQ.

This module defines the abstract base classes that all storage implementations
must follow, ensuring consistent interfaces across different backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator, Iterator
from datetime import datetime

from ..models.task import Task
from ..models.result import TaskResult
from ..models.event import TaskEvent
from ..models.schedule import Schedule


class BaseTaskQueue(ABC):
    """
    Abstract base class for task queue implementations.
    
    This interface defines the contract that all task queue backends
    must implement, supporting both async and sync operations.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def enqueue(self, task: Task) -> str:
        """
        Enqueue a task for processing.
        
        Args:
            task: The task to enqueue
            
        Returns:
            The task ID
        """
        pass
    
    @abstractmethod
    async def dequeue(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """
        Dequeue a task from the specified queues.
        
        Args:
            queues: List of queue names to check (in priority order)
            timeout: Maximum time to wait for a task (None = no timeout)
            
        Returns:
            The next available task or None if timeout reached
        """
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task or None if not found
        """
        pass
    
    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """
        Update a task in the queue.
        
        Args:
            task: The updated task
        """
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the queue.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if task was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_tasks(
        self, 
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """
        List tasks in the queue.
        
        Args:
            queue_name: Filter by queue name
            status: Filter by task status
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            
        Returns:
            List of tasks
        """
        pass
    
    @abstractmethod
    async def get_queue_size(self, queue_name: str) -> int:
        """
        Get the number of tasks in a queue.
        
        Args:
            queue_name: The queue name
            
        Returns:
            Number of tasks in the queue
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks.
        
        Returns:
            Number of tasks cleaned up
        """
        pass
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class BaseResultStorage(ABC):
    """
    Abstract base class for result storage implementations.
    
    This interface defines the contract that all result storage backends
    must implement, supporting both async and sync operations.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """
        Get a task result by task ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task result or None if not found
        """
        pass
    
    @abstractmethod
    async def set(self, result: TaskResult) -> None:
        """
        Store a task result.
        
        Args:
            result: The task result to store
        """
        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """
        Delete a task result.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if result was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_results(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """
        List task results.
        
        Args:
            status: Filter by result status
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of task results
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_results(self) -> int:
        """
        Clean up expired results.
        
        Returns:
            Number of results cleaned up
        """
        pass
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class BaseEventStorage(ABC):
    """
    Abstract base class for event storage implementations.
    
    This interface defines the contract that all event storage backends
    must implement for logging task lifecycle events.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def log_event(self, event: TaskEvent) -> None:
        """
        Log a task event.
        
        Args:
            event: The event to log
        """
        pass
    
    @abstractmethod
    async def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """
        Get task events.
        
        Args:
            task_id: Filter by task ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of task events
        """
        pass
    
    @abstractmethod
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """
        Clean up old events.
        
        Args:
            older_than: Delete events older than this timestamp
            
        Returns:
            Number of events cleaned up
        """
        pass
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class BaseScheduleStorage(ABC):
    """
    Abstract base class for schedule storage implementations.
    
    This interface defines the contract that all schedule storage backends
    must implement for managing scheduled tasks.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def save_schedule(self, schedule: Schedule) -> None:
        """
        Save a schedule.
        
        Args:
            schedule: The schedule to save
        """
        pass
    
    @abstractmethod
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get a schedule by ID.
        
        Args:
            schedule_id: The schedule ID
            
        Returns:
            The schedule or None if not found
        """
        pass
    
    @abstractmethod
    async def update_schedule(self, schedule: Schedule) -> None:
        """
        Update a schedule.
        
        Args:
            schedule: The updated schedule
        """
        pass
    
    @abstractmethod
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            schedule_id: The schedule ID
            
        Returns:
            True if schedule was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_schedules(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """
        List schedules.
        
        Args:
            status: Filter by schedule status
            limit: Maximum number of schedules to return
            offset: Number of schedules to skip
            
        Returns:
            List of schedules
        """
        pass
    
    @abstractmethod
    async def get_ready_schedules(self) -> List[Schedule]:
        """
        Get schedules that are ready to run.
        
        Returns:
            List of schedules ready to run
        """
        pass
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()