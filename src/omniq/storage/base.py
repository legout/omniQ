# src/omniq/storage/base.py
"""Base storage interfaces for OmniQ."""

from abc import ABC, abstractmethod
from typing import  Optional, Any, List, Dict
from datetime import datetime, timedelta

class BaseResultStorage(ABC):
    """Abstract base class for result storage."""
    
    @abstractmethod
    def store(
        self, 
        task_id: str, 
        result: Any, 
        status: str = "success", 
        error: Optional[str] = None, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Store a task result.
        
        Args:
            task_id: Task ID
            result: Result data
            status: Result status
            error: Error message
            ttl: Time-to-live for the result
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get(self, task_id: str, keep: bool = True) -> Optional[Any]:
        """
        Get a task result.
        
        Args:
            task_id: Task ID
            keep: Whether to keep the result after retrieval
            
        Returns:
            Result data or None if not found
        """
        pass


class BaseEventStorage(ABC):
    """Abstract base class for event storage."""
    
    @abstractmethod
    def log(
        self, 
        task_id: str, 
        event_type: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a task event.
        
        Args:
            task_id: Task ID
            event_type: Event type
            data: Event data
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_events(
        self, 
        task_id: Optional[str] = None, 
        event_type: Optional[str] = None, 
        start: Optional[datetime] = None, 
        end: Optional[datetime] = None
    ) -> List[Any]:
        """
        Get task events.
        
        Args:
            task_id: Filter by task ID
            event_type: Filter by event type
            start: Filter by start time
            end: Filter by end time
            
        Returns:
            List of events
        """
        pass