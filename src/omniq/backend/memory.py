"""Memory backend implementation for OmniQ.

This module provides the MemoryBackend class that creates instances of
memory-based storage components (queue, result storage).
"""

from typing import Dict, Any

from .base import BaseBackend
from ..queue.memory import MemoryQueue
from ..results.memory import MemoryResultStorage


class MemoryBackend(BaseBackend):
    """Memory-based backend implementation.
    
    This backend creates instances of memory-based storage components
    using fsspec.MemoryFileSystem for fast in-memory operations.
    
    Features:
    - Volatile storage (data lost on restart)
    - Fast in-memory operations
    - No external dependencies
    - Ideal for testing and short-lived applications
    """
    
    def __init__(self):
        """Initialize the memory backend."""
        config = {"backend_type": "memory"}
        super().__init__(config)
        self._queue: Optional[MemoryQueue] = None
        self._result_storage: Optional[MemoryResultStorage] = None
    
    def create_queue(self) -> MemoryQueue:
        """Create a memory-based task queue instance.
        
        Returns:
            A MemoryQueue instance
        """
        if not self._queue:
            self._queue = MemoryQueue()
        return self._queue
    
    def create_result_storage(self) -> MemoryResultStorage:
        """Create a memory-based result storage instance.
        
        Returns:
            A MemoryResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = MemoryResultStorage()
        return self._result_storage
    
    def create_event_storage(self) -> None:
        """Create a memory-based event storage instance.
        
        Note: Memory backend does not support event storage.
        
        Returns:
            None
            
        Raises:
            NotImplementedError: Always raised as memory backend doesn't support events
        """
        raise NotImplementedError("Memory backend does not support event storage")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the backend configuration.
        
        Returns:
            A dictionary containing the backend configuration
        """
        return {
            "backend_type": "memory"
        }