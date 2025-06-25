# src/omniq/queue/file.py
"""File task queue implementation for OmniQ."""

import os
import json
import uuid
from typing import List, Optional, Dict, Any, Union, Callable
from datetime import datetime, timedelta
import time
import fsspec
from fsspec.implementations.memory import MemoryFileSystem

from omniq.models.task import Task
from omniq.queue.base import BaseTaskQueue
from omniq.serialization.manager import SerializationManager

class FileTaskQueue(BaseTaskQueue):
    """Task queue implementation using fsspec for file storage."""
    
    def __init__(
        self, 
        project_name: str, 
        base_dir: str = ".",
        protocol: str = "file",
        storage_options: Dict[str, Any] | None = None,
        queues: List[str] | None = None,
        serialization_manager: SerializationManager | None = None,
        **kwargs
    ):
        """
        Initialize a file task queue.
        
        Args:
            project_name: Name of the project
            base_dir: Base directory for storage
            protocol: File system protocol (file, s3, gcs, azure, memory, etc.)
            storage_options: Options for the file system
            queues: List of queue names
            serialization_manager: Serialization manager for tasks
        """
        self.project_name = project_name
        self.base_dir = base_dir
        self.protocol = protocol
        self.storage_options = storage_options or {}
        self.queues = queues or ["default"]
        self.serialization_manager = serialization_manager or SerializationManager()
        
        # Create file system
        self.fs = fsspec.filesystem(self.protocol, **self.storage_options)
        
        # Create queue directories
        self._initialize_queues()
    
    def _initialize_queues(self):
        """Initialize queue directories."""
        for queue_name in self.queues:
            queue_path = self._get_queue_path(queue_name)
            self.fs.makedirs(queue_path, exist_ok=True)
    
    def _get_queue_path(self, queue_name: str) -> str:
        """Get the path for a queue."""
        if queue_name not in self.queues:
            raise ValueError(f"Queue '{queue_name}' is not defined")
        return os.path.join(self.base_dir, self.project_name, "queues", queue_name)
    
    def _get_task_path(self, queue_name: str, task_id: str) -> str:
        """Get the path for a task."""
        return os.path.join(self._get_queue_path(queue_name), f"{task_id}.task")
    
    def _get_metadata_path(self, queue_name: str, task_id: str) -> str:
        """Get the path for task metadata."""
        return os.path.join(self._get_queue_path(queue_name), f"{task_id}.meta")
    
    def _get_lock_path(self, queue_name: str, task_id: str) -> str:
        """Get the path for a task lock."""
        return os.path.join(self._get_queue_path(queue_name), f"{task_id}.lock")
    
    def enqueue(
        self, 
        func: Union[Callable, str], 
        func_args: Optional[Dict[str, Any]] = None, 
        queue_name: Optional[str] = None, 
        run_in: Optional[timedelta] = None, 
        ttl: Optional[timedelta] = None, 
        result_ttl: Optional[timedelta] = None
    ) -> str:
        """
        Enqueue a task.
        
        Args:
            func: Function to execute or function name
            func_args: Function arguments
            queue_name: Queue name
            run_in: Time to wait before execution
            ttl: Time-to-live for the task
            result_ttl: Time-to-live for the result
            
        Returns:
            Task ID
        """
        queue_name = queue_name or "default"
        if queue_name not in self.queues:
            raise ValueError(f"Queue '{queue_name}' is not defined")
        
        # Create task
        task = Task.create(
            func=func,
            func_args=func_args,
            queue_name=queue_name,
            run_in=run_in,
            ttl=ttl,
            result_ttl=result_ttl
        )
        
        # Serialize task
        task_data = self.serialization_manager.serialize(task)
        
        # Create metadata
        metadata = {
            "id": task.id,
            "queue_name": queue_name,
            "created_at": task.created_at.isoformat(),
            "scheduled_at": task.scheduled_at.isoformat(),
            "expires_at": task.expires_at.isoformat() if task.expires_at else None,
            "status": "pending"
        }
        
        # Write task and metadata
        task_path = self._get_task_path(queue_name, task.id)
        metadata_path = self._get_metadata_path(queue_name, task.id)
        
        with self.fs.open(task_path, 'wb') as f:
            f.write(task_data)
        
        with self.fs.open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        return task.id
    
    def dequeue(self, queue_names: Optional[List[str]] = None, limit: int = 1) -> List[Task]:
        """
        Dequeue tasks from queues.
        
        Args:
            queue_names: Queue names to dequeue from
            limit: Maximum number of tasks to dequeue
            
        Returns:
            List of tasks
        """
        queue_names = queue_names or ["default"]
        
        # Validate queue names
        for queue_name in queue_names:
            if queue_name not in self.queues:
                raise ValueError(f"Queue '{queue_name}' is not defined")
        
        tasks = []
        now = datetime.utcnow()
        
        # Process queues in order
        for queue_name in queue_names:
            if len(tasks) >= limit:
                break
            
            queue_path = self._get_queue_path(queue_name)
            
            # List all metadata files
            try:
                meta_files = [f for f in self.fs.find(queue_path) if f.endswith('.meta')]
            except Exception:
                # Directory might not exist or other error
                continue
            
            for meta_file in meta_files:
                if len(tasks) >= limit:
                    break
                
                # Read metadata
                try:
                    with self.fs.open(meta_file, 'r') as f:
                        metadata = json.load(f)
                except Exception:
                    # Skip invalid metadata
                    continue
                
                # Check if task is ready and not expired
                if metadata['status'] != 'pending':
                    continue
                
                scheduled_at = datetime.fromisoformat(metadata['scheduled_at'])
                if scheduled_at > now:
                    continue
                
                if metadata['expires_at']:
                    expires_at = datetime.fromisoformat(metadata['expires_at'])
                    if expires_at <= now:
                        # Task expired
                        metadata['status'] = 'expired'
                        with self.fs.open(meta_file, 'w') as f:
                            json.dump(metadata, f)
                        continue
                
                # Try to lock the task (simple file-based locking)
                lock_path = self._get_lock_path(queue_name, metadata['id'])
                try:
                    if self.fs.exists(lock_path):
                        # Task is locked by another worker
                        continue
                    
                    # Create lock file
                    with self.fs.open(lock_path, 'wb') as f:
                        f.write(b'')
                    
                    # Update metadata
                    metadata['status'] = 'processing'
                    with self.fs.open(meta_file, 'w') as f:
                        json.dump(metadata, f)
                    
                    # Read task
                    task_path = self._get_task_path(queue_name, metadata['id'])
                    with self.fs.open(task_path, 'rb') as f:
                        task_data = f.read()
                    
                    # Deserialize task
                    task = self.serialization_manager.deserialize(task_data)
                    tasks.append(task)
                    
                except Exception:
                    # Failed to lock or process task
                    if self.fs.exists(lock_path):
                        self.fs.rm(lock_path)
                    continue
        
        return tasks
    
    def complete(self, task_id: str, queue_name: Optional[str] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            queue_name: Queue name
            
        Returns:
            True if successful
        """
        if queue_name is None:
            # Find the queue that contains the task
            for q in self.queues:
                meta_path = self._get_metadata_path(q, task_id)
                if self.fs.exists(meta_path):
                    queue_name = q
                    break
            
            if queue_name is None:
                return False
        
        meta_path = self._get_metadata_path(queue_name, task_id)
        lock_path = self._get_lock_path(queue_name, task_id)
        
        if not self.fs.exists(meta_path):
            return False
        
        try:
            # Update metadata
            with self.fs.open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'completed'
            
            with self.fs.open(meta_path, 'w') as f:
                json.dump(metadata, f)
            
            # Remove lock
            if self.fs.exists(lock_path):
                self.fs.rm(lock_path)
            
            return True
        except Exception:
            return False
    
    def fail(self, task_id: str, queue_name: Optional[str] = None) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            queue_name: Queue name
            
        Returns:
            True if successful
        """
        if queue_name is None:
            # Find the queue that contains the task
            for q in self.queues:
                meta_path = self._get_metadata_path(q, task_id)
                if self.fs.exists(meta_path):
                    queue_name = q
                    break
            
            if queue_name is None:
                return False
        
        meta_path = self._get_metadata_path(queue_name, task_id)
        lock_path = self._get_lock_path(queue_name, task_id)
        
        if not self.fs.exists(meta_path):
            return False
        
        try:
            # Update metadata
            with self.fs.open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'failed'
            
            with self.fs.open(meta_path, 'w') as f:
                json.dump(metadata, f)
            
            # Remove lock
            if self.fs.exists(lock_path):
                self.fs.rm(lock_path)
            
            return True
        except Exception:
            return False