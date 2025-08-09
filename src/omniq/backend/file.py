"""File backend implementation for OmniQ.

This module provides the FileBackend class that creates instances of
file-based storage components (queue, result storage, event storage).
"""

from typing import Dict, Any, Optional

from .base import BaseBackend
from ..queue.file import FileQueue
from ..results.file import FileResultStorage
from ..events.file import FileEventStorage


class FileBackend(BaseBackend):
    """File-based backend implementation.
    
    This backend creates instances of file-based storage components
    using fsspec with support for local and cloud storage.
    
    Features:
    - Unified configuration for all file-based components
    - Support for local and cloud storage (S3, Azure, GCP)
    - Consistent storage options across components
    """
    
    def __init__(
        self,
        base_dir: str = "./omniq_data",
        storage_options: Optional[Dict[str, Any]] = None
    ):
        """Initialize the file backend.
        
        Args:
            base_dir: Base directory for all file storage
            storage_options: Additional options for fsspec filesystem
        """
        config = {
            "base_dir": base_dir,
            "storage_options": storage_options or {}
        }
        super().__init__(config)
        self.base_dir = base_dir
        self.storage_options = storage_options or {}
        self._queue: Optional[FileQueue] = None
        self._result_storage: Optional[FileResultStorage] = None
        self._event_storage: Optional[FileEventStorage] = None
    
    def create_queue(self) -> FileQueue:
        """Create a file-based task queue instance.
        
        Returns:
            A FileQueue instance
        """
        if not self._queue:
            self._queue = FileQueue(
                base_dir=self.base_dir,
                storage_options=self.storage_options
            )
        return self._queue
    
    def create_result_storage(self) -> FileResultStorage:
        """Create a file-based result storage instance.
        
        Returns:
            A FileResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = FileResultStorage(
                base_dir=self.base_dir,
                storage_options=self.storage_options
            )
        return self._result_storage
    
    def create_event_storage(self) -> FileEventStorage:
        """Create a file-based event storage instance.
        
        Returns:
            A FileEventStorage instance
        """
        if not self._event_storage:
            self._event_storage = FileEventStorage(
                base_dir=self.base_dir,
                storage_options=self.storage_options
            )
        return self._event_storage
    
    def get_config(self) -> Dict[str, Any]:
        """Get the backend configuration.
        
        Returns:
            A dictionary containing the backend configuration
        """
        return {
            "backend_type": "file",
            "base_dir": self.base_dir,
            "storage_options": self.storage_options
        }