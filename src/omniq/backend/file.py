# src/omniq/backend/file.py
"""File backend for OmniQ."""

import os
from typing import List, Optional, Dict, Any
import json
import fsspec
from fsspec.implementations.memory import MemoryFileSystem
from fsspec.implementations.dirfs import DirFileSystem

from omniq.backend.base import Backend

class FileBackend(Backend):
    """Backend implementation using fsspec for file storage."""

    def __init__(self, project_name: str, base_dir: str = ".", protocol: str = "file", storage_options: Dict[str, Any] = None):
        """
        Initialize a file backend.

        Args:
            project_name: Name of the project
            base_dir: Base directory for storage
            protocol: File system protocol (file, s3, gcs, azure, memory, etc.)
            storage_options: Options for the file system
        """
        self.project_name = project_name
        self.base_dir = base_dir
        self.protocol = protocol
        self.storage_options = storage_options or {}

        # Use DirFileSystem for local directory isolation
        if self.protocol != "memory":
            dir_path = os.path.join(self.base_dir, self.project_name)
            self.fs = DirFileSystem(dir_path, fsspec.filesystem(self.protocol, **self.storage_options))
            # Ensure base directory exists only for local filesystem
            if self.protocol == "file":
                os.makedirs(dir_path, exist_ok=True)
        else:
            self.fs = MemoryFileSystem()
        

    def _get_path(self, path: str) -> str:
        """Get the full path for a relative path."""
        return path or ""

    def create_task_queue(self, queues: List[str] = None, **kwargs):
        """Create a task queue from this backend."""
        from omniq.queue.file import FileTaskQueue
        return FileTaskQueue(
            project_name=self.project_name,
            base_dir=self.base_dir,
            protocol=self.protocol,
            storage_options=self.storage_options,
            queues=queues or ["default"],
            **kwargs
        )

    def create_result_store(self, **kwargs):
        """Create a result storage from this backend."""
        from omniq.storage.file import FileResultStorage
        return FileResultStorage(
            project_name=self.project_name,
            base_dir=self.base_dir,
            protocol=self.protocol,
            storage_options=self.storage_options,
            **kwargs
        )

    def create_event_store(self, **kwargs):
        """Create an event storage from this backend."""
        from omniq.storage.file import FileEventStorage
        return FileEventStorage(
            project_name=self.project_name,
            base_dir=self.base_dir,
            protocol=self.protocol,
            storage_options=self.storage_options,
            **kwargs
        )
