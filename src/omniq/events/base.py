"""Base event storage interface for OmniQ.

This module defines the abstract base class for event logging operations:
- BaseEventStorage: Interface for event logging operations

All interfaces follow the "Async First, Sync Wrapped" principle.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, AsyncIterator, Iterator
from datetime import datetime
import uuid

from ..models.event import TaskEvent


class BaseEventStorage(ABC):
    """Abstract base class for event storage operations.
    
    Provides both async and sync methods for logging and retrieving task lifecycle events.
    """
    
    @abstractmethod
    async def log_event_async(self, event: TaskEvent) -> None:
        """Log a task event asynchronously.
        
        Args:
            event: The event to log
        """
        pass
    
    @abstractmethod
    async def get_events_async(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Get all events for a task asynchronously.
        
        Args:
            task_id: ID of the task whose events to retrieve
            
        Returns:
            List of events for the task, ordered by timestamp
        """
        pass
    
    @abstractmethod
    async def get_events_by_type_async(self, event_type: str, limit: Optional[int] = None) -> AsyncIterator[TaskEvent]:
        """Get events by type asynchronously.
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return (None for no limit)
            
        Yields:
            Events matching the type
        """
        pass
    
    @abstractmethod
    async def get_events_in_range_async(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[TaskEvent]:
        """Get events within a time range asynchronously.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            task_id: Optional task ID to filter by
            
        Yields:
            Events within the time range
        """
        pass
    
    @abstractmethod
    async def cleanup_old_events_async(self, older_than: datetime) -> int:
        """Clean up old events asynchronously.
        
        Args:
            older_than: Delete events older than this timestamp
            
        Returns:
            Number of events cleaned up
        """
        pass
    
    # Sync wrapper methods (to be implemented by concrete classes)
    def log_event(self, event: TaskEvent) -> None:
        """Synchronous wrapper for log_event_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_events(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_by_type_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_in_range_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def cleanup_old_events(self, older_than: datetime) -> int:
        """Synchronous wrapper for cleanup_old_events_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")