"""Base backend interface for OmniQ.

This module defines the abstract base class for backend implementations.
Backends act as factories for creating storage component instances.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events.base import BaseEventStorage


class BaseBackend(ABC):
    """Abstract base class for backend implementations.
    
    Backends are responsible for creating and managing instances of storage components
    (queue, result storage, event storage) from a unified configuration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the backend with configuration.
        
        Args:
            config: Backend-specific configuration dictionary
        """
        self.config = config
    
    @abstractmethod
    async def initialize_async(self) -> None:
        """Initialize the backend asynchronously.
        
        This method should set up any necessary resources, connections,
        database schemas, etc.
        """
        pass
    
    @abstractmethod
    async def close_async(self) -> None:
        """Close the backend and clean up resources asynchronously.
        
        This method should close connections, clean up temporary resources, etc.
        """
        pass
    
    @abstractmethod
    def create_queue(self) -> BaseQueue:
        """Create a task queue instance.
        
        Returns:
            A queue instance implementing BaseQueue
        """
        pass
    
    @abstractmethod
    def create_result_storage(self) -> BaseResultStorage:
        """Create a result storage instance.
        
        Returns:
            A result storage instance implementing BaseResultStorage
        """
        pass
    
    @abstractmethod
    def create_event_storage(self) -> BaseEventStorage:
        """Create an event storage instance.
        
        Returns:
            An event storage instance implementing BaseEventStorage
        """
        pass
    
    # Sync wrapper methods (to be implemented by concrete classes)
    def initialize(self) -> None:
        """Synchronous wrapper for initialize_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        raise NotImplementedError("Sync wrapper must be implemented by concrete class")
    
    # Context manager support for async
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_async()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_async()
    
    # Context manager support for sync (to be implemented by concrete classes)
    def __enter__(self):
        """Sync context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()