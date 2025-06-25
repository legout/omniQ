# src/omniq/backend/base.py
"""Base class for backends."""

from abc import ABC, abstractmethod
#from typing import Optional, List

class Backend(ABC):
    """Abstract base class for all backends."""
    
    @abstractmethod
    def create_task_queue(self, **kwargs):
        """Create a task queue from this backend."""
        pass
    
    @abstractmethod
    def create_result_store(self, **kwargs):
        """Create a result storage from this backend."""
        pass
    
    @abstractmethod
    def create_event_store(self, **kwargs):
        """Create an event storage from this backend."""
        pass