"""Abstract base interfaces for task queue, result storage, and event storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from ..models.event import TaskEvent
from ..models.result import TaskResult
from ..models.task import Task


class BaseTaskQueue(ABC):
    """Abstract base interface for task queue operations."""
    
    @abstractmethod
    async def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        pass
    
    @abstractmethod
    async def dequeue(self, queue_name: str = "default", timeout: Optional[float] = None) -> Optional[Task]:
        """Remove and return a task from the queue."""
        pass
    
    @abstractmethod
    async def peek(self, queue_name: str = "default", limit: int = 1) -> List[Task]:
        """Look at tasks in queue without removing them."""
        pass
    
    @abstractmethod
    async def size(self, queue_name: str = "default") -> int:
        """Get the number of tasks in the queue."""
        pass
    
    @abstractmethod
    async def clear(self, queue_name: str = "default") -> int:
        """Clear all tasks from the queue and return count of removed tasks."""
        pass
    
    @abstractmethod
    async def get_queues(self) -> List[str]:
        """Get list of all queue names."""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        pass
    
    @abstractmethod
    async def update_task(self, task: Task) -> bool:
        """Update an existing task."""
        pass
    
    @abstractmethod
    async def remove_task(self, task_id: str) -> bool:
        """Remove a specific task by ID."""
        pass
    
    @abstractmethod
    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """List tasks with optional filtering."""
        pass
    
    @abstractmethod
    async def count_tasks(
        self,
        queue_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count tasks with optional filtering."""
        pass
    
    # Context manager support
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    # Cleanup and maintenance
    @abstractmethod
    async def cleanup_expired_tasks(self) -> int:
        """Remove expired tasks and return count."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        pass


class BaseResultStorage(ABC):
    """Abstract base interface for task result storage."""
    
    @abstractmethod
    async def store_result(self, result: TaskResult) -> None:
        """Store a task result."""
        pass
    
    @abstractmethod
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        pass
    
    @abstractmethod
    async def delete_result(self, task_id: str) -> bool:
        """Delete a task result."""
        pass
    
    @abstractmethod
    async def list_results(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[TaskResult]:
        """List results with optional filtering."""
        pass
    
    @abstractmethod
    async def count_results(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count results with optional filtering."""
        pass
    
    @abstractmethod
    async def get_results_by_status(self, status: str) -> List[TaskResult]:
        """Get results by status."""
        pass
    
    @abstractmethod
    async def cleanup_expired_results(self) -> int:
        """Remove expired results and return count."""
        pass
    
    # Context manager support
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        pass


class BaseEventStorage(ABC):
    """Abstract base interface for task event storage."""
    
    @abstractmethod
    async def store_event(self, event: TaskEvent) -> None:
        """Store a task event."""
        pass
    
    @abstractmethod
    async def get_events(
        self,
        task_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get events for a specific task."""
        pass
    
    @abstractmethod
    async def get_events_by_type(
        self,
        event_type: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get events by type."""
        pass
    
    @abstractmethod
    async def list_events(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[TaskEvent]:
        """List events with optional filtering."""
        pass
    
    @abstractmethod
    async def count_events(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count events with optional filtering."""
        pass
    
    @abstractmethod
    async def delete_events(self, task_id: str) -> int:
        """Delete all events for a task."""
        pass
    
    @abstractmethod
    async def cleanup_expired_events(self) -> int:
        """Remove expired events and return count."""
        pass
    
    # Stream interface for real-time monitoring
    @abstractmethod
    async def stream_events(
        self,
        task_id: Optional[str] = None,
        event_types: Optional[List[str]] = None
    ) -> AsyncIterator[TaskEvent]:
        """Stream events in real-time."""
        pass
    
    # Context manager support
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        pass


# Synchronous wrapper interfaces for convenience
class TaskQueue:
    """Synchronous wrapper for BaseTaskQueue."""
    
    def __init__(self, async_queue: BaseTaskQueue):
        self._async_queue = async_queue
    
    def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        import anyio
        return anyio.from_thread.run(self._async_queue.enqueue, task)
    
    def dequeue(self, queue_name: str = "default", timeout: Optional[float] = None) -> Optional[Task]:
        """Remove and return a task from the queue."""
        import anyio
        return anyio.from_thread.run(self._async_queue.dequeue, queue_name, timeout)
    
    def peek(self, queue_name: str = "default", limit: int = 1) -> List[Task]:
        """Look at tasks in queue without removing them."""
        import anyio
        return anyio.from_thread.run(self._async_queue.peek, queue_name, limit)
    
    def size(self, queue_name: str = "default") -> int:
        """Get the number of tasks in the queue."""
        import anyio
        return anyio.from_thread.run(self._async_queue.size, queue_name)
    
    def clear(self, queue_name: str = "default") -> int:
        """Clear all tasks from the queue and return count of removed tasks."""
        import anyio
        return anyio.from_thread.run(self._async_queue.clear, queue_name)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        import anyio
        return anyio.from_thread.run(self._async_queue.get_task, task_id)
    
    def __enter__(self):
        """Sync context manager entry."""
        import anyio
        anyio.from_thread.run(self._async_queue.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        import anyio
        return anyio.from_thread.run(self._async_queue.__aexit__, exc_type, exc_val, exc_tb)


class ResultStorage:
    """Synchronous wrapper for BaseResultStorage."""
    
    def __init__(self, async_storage: BaseResultStorage):
        self._async_storage = async_storage
    
    def store_result(self, result: TaskResult) -> None:
        """Store a task result."""
        import anyio
        return anyio.from_thread.run(self._async_storage.store_result, result)
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        import anyio
        return anyio.from_thread.run(self._async_storage.get_result, task_id)
    
    def __enter__(self):
        """Sync context manager entry."""
        import anyio
        anyio.from_thread.run(self._async_storage.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        import anyio
        return anyio.from_thread.run(self._async_storage.__aexit__, exc_type, exc_val, exc_tb)


class EventStorage:
    """Synchronous wrapper for BaseEventStorage."""
    
    def __init__(self, async_storage: BaseEventStorage):
        self._async_storage = async_storage
    
    def store_event(self, event: TaskEvent) -> None:
        """Store a task event."""
        import anyio
        return anyio.from_thread.run(self._async_storage.store_event, event)
    
    def get_events(
        self,
        task_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get events for a specific task."""
        import anyio
        return anyio.from_thread.run(self._async_storage.get_events, task_id, limit, offset)
    
    def __enter__(self):
        """Sync context manager entry."""
        import anyio
        anyio.from_thread.run(self._async_storage.__aenter__)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        import anyio
        return anyio.from_thread.run(self._async_storage.__aexit__, exc_type, exc_val, exc_tb)