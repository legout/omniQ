# src/omniq/backend/memory.py
"""Memory backend for OmniQ."""

from typing import List, Optional
from fsspec.implementations.memory import MemoryFileSystem

from omniq.backend.base import Backend

class MemoryBackend(Backend):
    """Backend implementation using fsspec MemoryFileSystem."""
    
    def __init__(self, project_name: str):
        """
        Initialize a memory backend.
        
        Args:
            project_name: Name of the project
        """
        self.project_name = project_name
        self.fs = MemoryFileSystem()
        
        # Create project directory
        self.fs.makedirs(project_name, exist_ok=True)
    
    def create_task_queue(self, queues: List[str] = None, **kwargs):
        """Create a task queue from this backend."""
        from omniq.queue.memory import MemoryTaskQueue
        return MemoryTaskQueue(
            project_name=self.project_name,
            fs=self.fs,
            queues=queues or ["default"],
            **kwargs
        )
    
    def create_result_store(self, **kwargs):
        """Create a result storage from this backend."""
        from omniq.storage.memory import MemoryResultStorage
        return MemoryResultStorage(
            project_name=self.project_name,
            fs=self.fs,
            **kwargs
        )
    
    def create_event_store(self, **kwargs):
        """Create an event storage from this backend."""
        from omniq.storage.memory import MemoryEventStorage
        return MemoryEventStorage(
            project_name=self.project_name,
            fs=self.fs,
            **kwargs
        )