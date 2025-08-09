"""Base result storage interfaces for OmniQ.

This module defines the abstract base classes for result storage components:
- BaseResultStorage: Interface for result storage operations

All interfaces follow the "Async First, Sync Wrapped" principle.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, AsyncIterator, Iterator
from datetime import datetime, timedelta
import uuid

from ..models.result import TaskResult


class BaseResultStorage(ABC):
    """Abstract base class for result storage operations.
    
    Provides both async and sync methods for storing and retrieving task results.
    Supports TTL for automatic cleanup of expired results.
    """
    
    @abstractmethod
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously.
        
        Args:
            result: The task result to store
        """
        pass
    
    @abstractmethod
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously.
        
        Args:
            task_id: ID of the task whose result to retrieve
            
        Returns:
            The task result, or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously.
        
        Args:
            task_id: ID of the task whose result to delete
            
        Returns:
            True if result was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously.
        
        Returns:
            Number of results cleaned up
        """
        pass
    
    @abstractmethod
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously.
        
        Args:
            status: Status to filter by
            
        Yields:
            Task results matching the status
        """
        pass
    
    # Sync wrapper methods (to be implemented by concrete classes)
    def store_result(self, result: TaskResult) -> None:
        """Synchronous wrapper for store_result_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_result(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Synchronous wrapper for get_result_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def delete_result(self, task_id: uuid.UUID) -> bool:
        """Synchronous wrapper for delete_result_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def cleanup_expired(self) -> int:
        """Synchronous wrapper for cleanup_expired_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def get_results_by_status(self, status: str) -> Iterator[TaskResult]:
        """Synchronous wrapper for get_results_by_status_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")

