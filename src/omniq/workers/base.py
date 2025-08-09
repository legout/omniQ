"""Base worker interface for OmniQ.

This module defines the abstract base class for all worker implementations.
All workers follow the "Async First, Sync Wrapped" principle.
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import timedelta


class BaseWorker(ABC):
    """Abstract base class for all worker implementations.
    
    Defines the common interface that all worker types must implement.
    Workers are responsible for dequeuing tasks, executing them, and
    storing results and events.
    """
    
    @abstractmethod
    async def start(self) -> None:
        """Start the worker.
        
        This method should initialize any resources needed by the worker
        and begin processing tasks from the queue.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the worker gracefully.
        
        This method should stop processing new tasks and clean up
        any resources used by the worker.
        """
        pass
    
    @abstractmethod
    async def run(self) -> None:
        """Main worker loop for fetching and executing tasks.
        
        This method contains the core logic for:
        - Dequeuing tasks from the queue
        - Executing task functions (both sync and async)
        - Storing results in result storage
        - Logging lifecycle events to event storage
        - Respecting task timeouts and TTLs
        """
        pass