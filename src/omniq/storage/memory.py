"""
Memory storage implementation for OmniQ using fsspec.MemoryFileSystem.

This module provides memory-based implementations for task queue,
result storage, event storage, and schedule storage using fsspec
with MemoryFileSystem for fast in-memory operations without persistence.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import fsspec
import msgspec
from fsspec.implementations.memory import MemoryFileSystem

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent
from ..models.schedule import Schedule, ScheduleStatus, ScheduleType


class AsyncMemoryQueue(BaseTaskQueue):
    """
    Async memory-based task queue implementation using fsspec.MemoryFileSystem.
    
    This class implements the BaseTaskQueue interface using fsspec
    with MemoryFileSystem for fast in-memory task storage with support for
    multiple queues organized in directory structure.
    """
    
    def __init__(
        self,
        base_dir: str = "omniq_data",
        fs_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the memory-based task queue.
        
        Args:
            base_dir: Base directory for storing task files in memory
            fs_kwargs: Additional kwargs for fsspec filesystem
        """
        self.base_dir = Path(base_dir)
        self.fs_kwargs = fs_kwargs or {}
        self._fs: Optional[MemoryFileSystem] = None
        
        # Directory structure
        self.tasks_dir = self.base_dir / "tasks"
        self.queues_dir = self.base_dir / "queues"
    
    async def connect(self) -> None:
        """Connect to the memory file system."""
        if self._fs is not None:
            return
        
        # Create memory filesystem instance
        self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
        
        # Ensure directories exist
        await self._ensure_directories()
    
    async def disconnect(self) -> None:
        """Disconnect from the memory file system."""
        self._fs = None
    
    async def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Create base directories
        for dir_path in [self.tasks_dir, self.queues_dir]:
            dir_str = str(dir_path)
            if not self._fs.exists(dir_str):
                self._fs.makedirs(dir_str, exist_ok=True)
    
    def _get_task_path(self, task_id: str) -> str:
        """Get the file path for a task."""
        return str(self.tasks_dir / f"{task_id}.json")
    
    def _get_queue_path(self, queue_name: str) -> str:
        """Get the directory path for a queue."""
        return str(self.queues_dir / queue_name)
    
    def _get_queue_task_path(self, queue_name: str, task_id: str) -> str:
        """Get the symlink path for a task in a queue."""
        return str(self.queues_dir / queue_name / f"{task_id}.json")
    
    async def _write_task_file(self, task: Task) -> None:
        """Write task data to file."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        task_path = self._get_task_path(task.id)
        task_data = {
            "task_data": msgspec.json.encode(task).decode(),
            "metadata": {
                "id": task.id,
                "queue_name": task.queue_name,
                "priority": task.priority,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "run_at": task.run_at.isoformat() if task.run_at else None,
                "expires_at": task.expires_at.isoformat() if task.expires_at else None,
            }
        }
        
        with self._fs.open(task_path, "w") as f:
            json.dump(task_data, f, indent=2)
    
    async def _read_task_file(self, task_id: str) -> Optional[Task]:
        """Read task data from file."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        task_path = self._get_task_path(task_id)
        
        if not self._fs.exists(task_path):
            return None
        
        try:
            with self._fs.open(task_path, "r") as f:
                task_data = json.load(f)
            
            return msgspec.json.decode(task_data["task_data"], type=Task)
        except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
            return None
    
    async def _create_queue_link(self, task: Task) -> None:
        """Create a queue link for the task."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        queue_dir = self._get_queue_path(task.queue_name)
        if not self._fs.exists(queue_dir):
            self._fs.makedirs(queue_dir, exist_ok=True)
        
        queue_task_path = self._get_queue_task_path(task.queue_name, task.id)
        task_path = self._get_task_path(task.id)
        
        # For memory filesystem, we'll copy the file since symlinks aren't supported
        if not self._fs.exists(queue_task_path):
            self._fs.copy(task_path, queue_task_path)
    
    async def _remove_queue_link(self, task_id: str, queue_name: str) -> None:
        """Remove a queue link for the task."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        queue_task_path = self._get_queue_task_path(queue_name, task_id)
        if self._fs.exists(queue_task_path):
            self._fs.rm(queue_task_path)
    
    async def enqueue(self, task: Task) -> str:
        """Enqueue a task for processing."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Write task file
        await self._write_task_file(task)
        
        # Create queue link
        await self._create_queue_link(task)
        
        return task.id
    
    async def dequeue(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task from the specified queues."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Collect all pending tasks from specified queues
        pending_tasks = []
        
        for queue_name in queues:
            queue_dir = self._get_queue_path(queue_name)
            if not self._fs.exists(queue_dir):
                continue
            
            try:
                task_files = self._fs.ls(queue_dir)
                for task_file in task_files:
                    # Handle both string paths and file info dicts
                    if isinstance(task_file, dict):
                        file_path = task_file.get('name', '')
                    else:
                        file_path = task_file
                    
                    if file_path.endswith('.json'):
                        task_id = Path(file_path).stem
                        task = await self._read_task_file(task_id)
                        
                        if task and task.status == TaskStatus.PENDING:
                            # Check if task is ready to run
                            now = datetime.utcnow()
                            if task.run_at and task.run_at > now:
                                continue
                            if task.expires_at and task.expires_at <= now:
                                continue
                            
                            pending_tasks.append((task, queue_name))
            except Exception:
                continue
        
        if not pending_tasks:
            return None
        
        # Sort by priority (desc) and created_at (asc)
        pending_tasks.sort(key=lambda x: (-x[0].priority, x[0].created_at))
        
        # Get the highest priority task
        task, queue_name = pending_tasks[0]
        
        # Update task status to running
        task.status = TaskStatus.RUNNING
        await self._write_task_file(task)
        
        # Remove from queue
        await self._remove_queue_link(task.id, queue_name)
        
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return await self._read_task_file(task_id)
    
    async def update_task(self, task: Task) -> None:
        """Update a task in the queue."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Write updated task file
        await self._write_task_file(task)
        
        # If task is pending, ensure queue link exists
        if task.status == TaskStatus.PENDING:
            await self._create_queue_link(task)
        else:
            # Remove from queue if not pending
            await self._remove_queue_link(task.id, task.queue_name)
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task from the queue."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        task = await self._read_task_file(task_id)
        if task is None:
            return False
        
        # Remove queue link
        await self._remove_queue_link(task_id, task.queue_name)
        
        # Remove task file
        task_path = self._get_task_path(task_id)
        if self._fs.exists(task_path):
            self._fs.rm(task_path)
            return True
        
        return False
    
    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """List tasks in the queue."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        tasks = []
        
        if queue_name:
            # List tasks from specific queue
            queue_dir = self._get_queue_path(queue_name)
            if self._fs.exists(queue_dir):
                try:
                    task_files = self._fs.ls(queue_dir)
                    for task_file in task_files:
                        # Handle both string paths and file info dicts
                        if isinstance(task_file, dict):
                            file_path = task_file.get('name', '')
                        else:
                            file_path = task_file
                        
                        if file_path.endswith('.json'):
                            task_id = Path(file_path).stem
                            task = await self._read_task_file(task_id)
                            if task:
                                tasks.append(task)
                except Exception:
                    pass
        else:
            # List all tasks
            if self._fs.exists(str(self.tasks_dir)):
                try:
                    task_files = self._fs.ls(str(self.tasks_dir))
                    for task_file in task_files:
                        # Handle both string paths and file info dicts
                        if isinstance(task_file, dict):
                            file_path = task_file.get('name', '')
                        else:
                            file_path = task_file
                        
                        if file_path.endswith('.json'):
                            task_id = Path(file_path).stem
                            task = await self._read_task_file(task_id)
                            if task:
                                tasks.append(task)
                except Exception:
                    pass
        
        # Filter by status if specified
        if status:
            tasks = [task for task in tasks if task.status.value == status]
        
        # Sort by priority (desc) and created_at (asc)
        tasks.sort(key=lambda x: (-x.priority, x.created_at))
        
        # Apply offset and limit
        if offset > 0:
            tasks = tasks[offset:]
        if limit is not None:
            tasks = tasks[:limit]
        
        return tasks
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Get the number of tasks in a queue."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        queue_dir = self._get_queue_path(queue_name)
        if not self._fs.exists(queue_dir):
            return 0
        
        try:
            task_files = self._fs.ls(queue_dir)
            count = 0
            for f in task_files:
                # Handle both string paths and file info dicts
                if isinstance(f, dict):
                    file_path = f.get('name', '')
                else:
                    file_path = f
                
                if file_path.endswith('.json'):
                    count += 1
            return count
        except Exception:
            return 0
    
    async def cleanup_expired_tasks(self) -> int:
        """Clean up expired tasks."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        cleaned_count = 0
        now = datetime.utcnow()
        
        if not self._fs.exists(str(self.tasks_dir)):
            return 0
        
        try:
            task_files = self._fs.ls(str(self.tasks_dir))
            for task_file in task_files:
                # Handle both string paths and file info dicts
                if isinstance(task_file, dict):
                    file_path = task_file.get('name', '')
                else:
                    file_path = task_file
                
                if file_path.endswith('.json'):
                    task_id = Path(file_path).stem
                    task = await self._read_task_file(task_id)
                    
                    if task and task.expires_at and task.expires_at <= now:
                        await self.delete_task(task_id)
                        cleaned_count += 1
        except Exception:
            pass
        
        return cleaned_count


class MemoryQueue(AsyncMemoryQueue):
    """
    Synchronous wrapper around AsyncMemoryQueue.
    
    This class provides a synchronous interface to the async memory queue
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the memory file system (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we can't use asyncio.run()
            # Instead, we'll connect directly since memory filesystem is synchronous
            if self._fs is not None:
                return
            
            # Create memory filesystem instance
            import fsspec
            self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
            
            # Ensure directories exist synchronously
            self._ensure_directories_sync()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            asyncio.run(self.connect())
    
    def _ensure_directories_sync(self) -> None:
        """Ensure required directories exist (sync version)."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Create base directories
        for dir_path in [self.tasks_dir, self.queues_dir]:
            dir_str = str(dir_path)
            if not self._fs.exists(dir_str):
                self._fs.makedirs(dir_str, exist_ok=True)
    
    def disconnect_sync(self) -> None:
        """Disconnect from the memory file system (sync)."""
        asyncio.run(self.disconnect())
    
    def enqueue_sync(self, task: Task) -> str:
        """Enqueue a task for processing (sync)."""
        return asyncio.run(self.enqueue(task))
    
    def dequeue_sync(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task from the specified queues (sync)."""
        return asyncio.run(self.dequeue(queues, timeout))
    
    def get_task_sync(self, task_id: str) -> Optional[Task]:
        """Get a task by ID (sync)."""
        return asyncio.run(self.get_task(task_id))
    
    def update_task_sync(self, task: Task) -> None:
        """Update a task in the queue (sync)."""
        asyncio.run(self.update_task(task))
    
    def delete_task_sync(self, task_id: str) -> bool:
        """Delete a task from the queue (sync)."""
        return asyncio.run(self.delete_task(task_id))
    
    def list_tasks_sync(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """List tasks in the queue (sync)."""
        return asyncio.run(self.list_tasks(queue_name, status, limit, offset))
    
    def get_queue_size_sync(self, queue_name: str) -> int:
        """Get the number of tasks in a queue (sync)."""
        return asyncio.run(self.get_queue_size(queue_name))
    
    def cleanup_expired_tasks_sync(self) -> int:
        """Clean up expired tasks (sync)."""
        return asyncio.run(self.cleanup_expired_tasks())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncMemoryResultStorage(BaseResultStorage):
    """
    Async memory-based result storage implementation using fsspec.MemoryFileSystem.
    
    This class implements the BaseResultStorage interface using fsspec
    with MemoryFileSystem for fast in-memory result storage.
    """
    
    def __init__(
        self,
        base_dir: str = "omniq_data",
        fs_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the memory-based result storage.
        
        Args:
            base_dir: Base directory for storing result files in memory
            fs_kwargs: Additional kwargs for fsspec filesystem
        """
        self.base_dir = Path(base_dir)
        self.fs_kwargs = fs_kwargs or {}
        self._fs: Optional[MemoryFileSystem] = None
        
        # Directory structure
        self.results_dir = self.base_dir / "results"
    
    async def connect(self) -> None:
        """Connect to the memory file system."""
        if self._fs is not None:
            return
        
        # Create memory filesystem instance
        self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
        
        # Ensure directories exist
        await self._ensure_directories()
    
    async def disconnect(self) -> None:
        """Disconnect from the memory file system."""
        self._fs = None
    
    async def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        results_dir_str = str(self.results_dir)
        if not self._fs.exists(results_dir_str):
            self._fs.makedirs(results_dir_str, exist_ok=True)
    
    def _get_result_path(self, task_id: str) -> str:
        """Get the file path for a result."""
        return str(self.results_dir / f"{task_id}.json")
    
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        result_path = self._get_result_path(task_id)
        
        if not self._fs.exists(result_path):
            return None
        
        try:
            with self._fs.open(result_path, "r") as f:
                result_data = json.load(f)
            
            return msgspec.json.decode(result_data["result_data"], type=TaskResult)
        except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
            return None
    
    async def set(self, result: TaskResult) -> None:
        """Store a task result."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        result_path = self._get_result_path(result.task_id)
        result_data = {
            "result_data": msgspec.json.encode(result).decode(),
            "metadata": {
                "task_id": result.task_id,
                "status": result.status.value,
                "created_at": result.created_at.isoformat(),
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "expires_at": result.expires_at.isoformat() if result.expires_at else None,
            }
        }
        
        with self._fs.open(result_path, "w") as f:
            json.dump(result_data, f, indent=2)
    
    async def delete(self, task_id: str) -> bool:
        """Delete a task result."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        result_path = self._get_result_path(task_id)
        if self._fs.exists(result_path):
            self._fs.rm(result_path)
            return True
        
        return False
    
    async def list_results(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """List task results."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        results = []
        
        if not self._fs.exists(str(self.results_dir)):
            return results
        
        try:
            result_files = self._fs.ls(str(self.results_dir))
            for result_file in result_files:
                # Handle both string paths and file info dicts
                if isinstance(result_file, dict):
                    file_path = result_file.get('name', '')
                else:
                    file_path = result_file
                
                if file_path.endswith('.json'):
                    task_id = Path(file_path).stem
                    result = await self.get(task_id)
                    if result:
                        results.append(result)
        except Exception:
            pass
        
        # Filter by status if specified
        if status:
            results = [result for result in results if result.status.value == status]
        
        # Sort by completed_at (desc)
        results.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
        
        # Apply offset and limit
        if offset > 0:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]
        
        return results
    
    async def cleanup_expired_results(self) -> int:
        """Clean up expired results."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        cleaned_count = 0
        now = datetime.utcnow()
        
        if not self._fs.exists(str(self.results_dir)):
            return 0
        
        try:
            result_files = self._fs.ls(str(self.results_dir))
            for result_file in result_files:
                # Handle both string paths and file info dicts
                if isinstance(result_file, dict):
                    file_path = result_file.get('name', '')
                else:
                    file_path = result_file
                
                if file_path.endswith('.json'):
                    task_id = Path(file_path).stem
                    result = await self.get(task_id)
                    
                    if result and result.expires_at and result.expires_at <= now:
                        await self.delete(task_id)
                        cleaned_count += 1
        except Exception:
            pass
        
        return cleaned_count


class MemoryResultStorage(AsyncMemoryResultStorage):
    """
    Synchronous wrapper around AsyncMemoryResultStorage.
    
    This class provides a synchronous interface to the async memory result storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the memory file system (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we can't use asyncio.run()
            # Instead, we'll connect directly since memory filesystem is synchronous
            if self._fs is not None:
                return
            
            # Create memory filesystem instance
            import fsspec
            self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
            
            # Ensure directories exist synchronously
            self._ensure_directories_sync()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            asyncio.run(self.connect())
    
    def _ensure_directories_sync(self) -> None:
        """Ensure required directories exist (sync version)."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        # Create base directories
        results_dir_str = str(self.results_dir)
        if not self._fs.exists(results_dir_str):
            self._fs.makedirs(results_dir_str, exist_ok=True)
    
    def disconnect_sync(self) -> None:
        """Disconnect from the memory file system (sync)."""
        asyncio.run(self.disconnect())
    
    def get_sync(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID (sync)."""
        return asyncio.run(self.get(task_id))
    
    def set_sync(self, result: TaskResult) -> None:
        """Store a task result (sync)."""
        asyncio.run(self.set(result))
    
    def delete_sync(self, task_id: str) -> bool:
        """Delete a task result (sync)."""
        return asyncio.run(self.delete(task_id))
    
    def list_results_sync(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """List task results (sync)."""
        return asyncio.run(self.list_results(status, limit, offset))
    
    def cleanup_expired_results_sync(self) -> int:
        """Clean up expired results (sync)."""
        return asyncio.run(self.cleanup_expired_results())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncMemoryEventStorage(BaseEventStorage):
    """
    Async memory-based event storage implementation using fsspec.MemoryFileSystem.
    
    This class implements the BaseEventStorage interface using fsspec
    with MemoryFileSystem for fast in-memory event logging as JSON files.
    """
    
    def __init__(
        self,
        base_dir: str = "omniq_data",
        fs_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the memory-based event storage.
        
        Args:
            base_dir: Base directory for storing event files in memory
            fs_kwargs: Additional kwargs for fsspec filesystem
        """
        self.base_dir = Path(base_dir)
        self.fs_kwargs = fs_kwargs or {}
        self._fs: Optional[MemoryFileSystem] = None
        
        # Directory structure
        self.events_dir = self.base_dir / "events"
    
    async def connect(self) -> None:
        """Connect to the memory file system."""
        if self._fs is not None:
            return
        
        # Create memory filesystem instance
        self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
        
        # Ensure directories exist
        await self._ensure_directories()
    
    async def disconnect(self) -> None:
        """Disconnect from the memory file system."""
        self._fs = None
    
    async def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        events_dir_str = str(self.events_dir)
        if not self._fs.exists(events_dir_str):
            self._fs.makedirs(events_dir_str, exist_ok=True)
    
    def _get_event_path(self, event_id: str) -> str:
        """Get the file path for an event."""
        return str(self.events_dir / f"{event_id}.json")
    
    async def log_event(self, event: TaskEvent) -> None:
        """Log a task event."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        event_path = self._get_event_path(event.id)
        event_data = {
            "event_data": msgspec.json.encode(event).decode(),
            "metadata": {
                "id": event.id,
                "task_id": event.task_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "worker_id": event.worker_id,
                "queue_name": event.queue_name,
            }
        }
        
        with self._fs.open(event_path, "w") as f:
            json.dump(event_data, f, indent=2)
    
    async def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get task events."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        events = []
        
        if not self._fs.exists(str(self.events_dir)):
            return events
        
        try:
            event_files = self._fs.ls(str(self.events_dir))
            for event_file in event_files:
                # Handle both string paths and file info dicts
                if isinstance(event_file, dict):
                    file_path = event_file.get('name', '')
                else:
                    file_path = event_file
                
                if file_path.endswith('.json'):
                    try:
                        with self._fs.open(file_path, "r") as f:
                            event_data = json.load(f)
                        
                        event = msgspec.json.decode(event_data["event_data"], type=TaskEvent)
                        
                        # Apply filters
                        if task_id and event.task_id != task_id:
                            continue
                        if event_type and event.event_type.value != event_type:
                            continue
                        if start_time and event.timestamp < start_time:
                            continue
                        if end_time and event.timestamp > end_time:
                            continue
                        
                        events.append(event)
                    except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
                        continue
        except Exception:
            pass
        
        # Sort by timestamp (desc)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply offset and limit
        if offset > 0:
            events = events[offset:]
        if limit is not None:
            events = events[:limit]
        
        return events
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """Clean up old events."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        cleaned_count = 0
        
        if not self._fs.exists(str(self.events_dir)):
            return 0
        
        try:
            event_files = self._fs.ls(str(self.events_dir))
            for event_file in event_files:
                # Handle both string paths and file info dicts
                if isinstance(event_file, dict):
                    file_path = event_file.get('name', '')
                else:
                    file_path = event_file
                
                if file_path.endswith('.json'):
                    try:
                        with self._fs.open(file_path, "r") as f:
                            event_data = json.load(f)
                        
                        event = msgspec.json.decode(event_data["event_data"], type=TaskEvent)
                        
                        if event.timestamp < older_than:
                            self._fs.rm(file_path)
                            cleaned_count += 1
                    except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
                        continue
        except Exception:
            pass
        
        return cleaned_count


class MemoryEventStorage(AsyncMemoryEventStorage):
    """
    Synchronous wrapper around AsyncMemoryEventStorage.
    
    This class provides a synchronous interface to the async memory event storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the memory file system (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we can't use asyncio.run()
            # Instead, we'll connect directly since memory filesystem is synchronous
            if self._fs is not None:
                return
            
            # Create memory filesystem instance
            import fsspec
            self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
            
            # Ensure directories exist synchronously
            self._ensure_directories_sync()
        except RuntimeError:
            # No running event loop, safe to use asyncio.run()
            asyncio.run(self.connect())
    
    def _ensure_directories_sync(self) -> None:
        """Ensure required directories exist (sync version)."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        events_dir_str = str(self.events_dir)
        if not self._fs.exists(events_dir_str):
            self._fs.makedirs(events_dir_str, exist_ok=True)
    
    def disconnect_sync(self) -> None:
        """Disconnect from the memory file system (sync)."""
        asyncio.run(self.disconnect())
    
    def log_event_sync(self, event: TaskEvent) -> None:
        """Log a task event (sync)."""
        asyncio.run(self.log_event(event))
    
    def get_events_sync(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get task events (sync)."""
        return asyncio.run(self.get_events(task_id, event_type, start_time, end_time, limit, offset))
    
    def cleanup_old_events_sync(self, older_than: datetime) -> int:
        """Clean up old events (sync)."""
        return asyncio.run(self.cleanup_old_events(older_than))
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncMemoryScheduleStorage(BaseScheduleStorage):
    """
    Async memory-based schedule storage implementation using fsspec.MemoryFileSystem.
    
    This class implements the BaseScheduleStorage interface using fsspec
    with MemoryFileSystem for fast in-memory schedule storage and management.
    """
    
    def __init__(
        self,
        base_dir: str = "omniq_data",
        fs_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the memory-based schedule storage.
        
        Args:
            base_dir: Base directory for storing schedule files in memory
            fs_kwargs: Additional kwargs for fsspec filesystem
        """
        self.base_dir = Path(base_dir)
        self.fs_kwargs = fs_kwargs or {}
        self._fs: Optional[MemoryFileSystem] = None
        
        # Directory structure
        self.schedules_dir = self.base_dir / "schedules"
    
    async def connect(self) -> None:
        """Connect to the memory file system."""
        if self._fs is not None:
            return
        
        # Create memory filesystem instance
        self._fs = fsspec.filesystem("memory", **self.fs_kwargs)
        
        # Ensure directories exist
        await self._ensure_directories()
    
    async def disconnect(self) -> None:
        """Disconnect from the memory file system."""
        self._fs = None
    
    async def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        schedules_dir_str = str(self.schedules_dir)
        if not self._fs.exists(schedules_dir_str):
            self._fs.makedirs(schedules_dir_str, exist_ok=True)
    
    def _get_schedule_path(self, schedule_id: str) -> str:
        """Get the file path for a schedule."""
        return str(self.schedules_dir / f"{schedule_id}.json")
    
    async def save_schedule(self, schedule: Schedule) -> None:
        """Save a schedule."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        schedule_path = self._get_schedule_path(schedule.id)
        
        # Convert schedule to dict and handle func field
        schedule_dict = schedule.to_dict()
        if callable(schedule_dict.get('func')):
            schedule_dict['func'] = schedule_dict['func'].__name__
        
        schedule_data = {
            "schedule_data": json.dumps(schedule_dict),
            "metadata": {
                "id": schedule.id,
                "schedule_type": schedule.schedule_type.value,
                "status": schedule.status.value,
                "created_at": schedule.created_at.isoformat(),
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "expires_at": schedule.expires_at.isoformat() if schedule.expires_at else None,
            }
        }
        
        with self._fs.open(schedule_path, "w") as f:
            json.dump(schedule_data, f, indent=2)
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        schedule_path = self._get_schedule_path(schedule_id)
        
        if not self._fs.exists(schedule_path):
            return None
        
        try:
            with self._fs.open(schedule_path, "r") as f:
                schedule_data = json.load(f)
            
            # Parse the schedule data from JSON
            schedule_dict = json.loads(schedule_data["schedule_data"])
            
            # Convert datetime strings back to datetime objects
            for field in ['created_at', 'last_run', 'next_run', 'expires_at', 'timestamp']:
                if field in schedule_dict and schedule_dict[field] is not None:
                    schedule_dict[field] = datetime.fromisoformat(schedule_dict[field])
            
            # Convert interval back to timedelta if present
            if 'interval' in schedule_dict and schedule_dict['interval'] is not None:
                interval_data = schedule_dict['interval']
                if isinstance(interval_data, dict):
                    schedule_dict['interval'] = timedelta(**interval_data)
                elif isinstance(interval_data, (int, float)):
                    schedule_dict['interval'] = timedelta(seconds=interval_data)
            
            # Convert enums back
            if 'schedule_type' in schedule_dict:
                schedule_dict['schedule_type'] = ScheduleType(schedule_dict['schedule_type'])
            if 'status' in schedule_dict:
                schedule_dict['status'] = ScheduleStatus(schedule_dict['status'])
            
            # Create Schedule object directly
            return Schedule(**schedule_dict)
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError):
            return None
    
    async def update_schedule(self, schedule: Schedule) -> None:
        """Update a schedule."""
        await self.save_schedule(schedule)
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        schedule_path = self._get_schedule_path(schedule_id)
        if self._fs.exists(schedule_path):
            self._fs.rm(schedule_path)
            return True
        
        return False
    
    async def list_schedules(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        schedules = []
        
        if not self._fs.exists(str(self.schedules_dir)):
            return schedules
        
        try:
            schedule_files = self._fs.ls(str(self.schedules_dir))
            for schedule_file in schedule_files:
                # Handle both string paths and file info dicts
                if isinstance(schedule_file, dict):
                    file_path = schedule_file.get('name', '')
                else:
                    file_path = schedule_file
                
                if file_path.endswith('.json'):
                    schedule_id = Path(file_path).stem
                    schedule = await self.get_schedule(schedule_id)
                    if schedule:
                        schedules.append(schedule)
        except Exception:
            pass
        
        # Filter by status if specified
        if status:
            schedules = [schedule for schedule in schedules if schedule.status.value == status]
        
        # Sort by created_at (desc)
        schedules.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply offset and limit
        if offset > 0:
            schedules = schedules[offset:]
        if limit is not None:
            schedules = schedules[:limit]
        
        return schedules
    
    async def get_ready_schedules(self) -> List[Schedule]:
        """Get schedules that are ready to run."""
        if self._fs is None:
            raise RuntimeError("Filesystem not connected")
        
        ready_schedules = []
        now = datetime.utcnow()
        
        if not self._fs.exists(str(self.schedules_dir)):
            return ready_schedules
        
        try:
            schedule_files = self._fs.ls(str(self.schedules_dir))
            for schedule_file in schedule_files:
                # Handle both string paths and file info dicts
                if isinstance(schedule_file, dict):
                    file_path = schedule_file.get('name', '')
                else:
                    file_path = schedule_file
                
                if file_path.endswith('.json'):
                    schedule_id = Path(file_path).stem
                    schedule = await self.get_schedule(schedule_id)
                    
                    if schedule and schedule.status == ScheduleStatus.ACTIVE:
                        if schedule.next_run and schedule.next_run <= now:
                            if not schedule.expires_at or schedule.expires_at > now:
                                ready_schedules.append(schedule)
        except Exception:
            pass
        
        # Sort by next_run (asc)
        ready_schedules.sort(key=lambda x: x.next_run or datetime.min)
        
        return ready_schedules


class MemoryScheduleStorage(AsyncMemoryScheduleStorage):
    """
    Synchronous wrapper around AsyncMemoryScheduleStorage.
    
    This class provides a synchronous interface to the async memory schedule storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the memory file system (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from the memory file system (sync)."""
        asyncio.run(self.disconnect())
    
    def save_schedule_sync(self, schedule: Schedule) -> None:
        """Save a schedule (sync)."""
        asyncio.run(self.save_schedule(schedule))
    
    def get_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID (sync)."""
        return asyncio.run(self.get_schedule(schedule_id))
    
    def update_schedule_sync(self, schedule: Schedule) -> None:
        """Update a schedule (sync)."""
        asyncio.run(self.update_schedule(schedule))
    
    def delete_schedule_sync(self, schedule_id: str) -> bool:
        """Delete a schedule (sync)."""
        return asyncio.run(self.delete_schedule(schedule_id))
    
    def list_schedules_sync(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules (sync)."""
        return asyncio.run(self.list_schedules(status, limit, offset))
    
    def get_ready_schedules_sync(self) -> List[Schedule]:
        """Get schedules that are ready to run (sync)."""
        return asyncio.run(self.get_ready_schedules())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class MemoryBackend:
    """
    Unified memory storage backend for OmniQ.
    
    This backend provides in-memory storage using fsspec's MemoryFileSystem,
    suitable for testing, development, and scenarios where persistence is not required.
    All data is stored in memory and will be lost when the process terminates.
    """
    
    def __init__(self, base_path: str = "/omniq"):
        """
        Initialize the memory backend.
        
        Args:
            base_path: Base path for all storage operations in the memory filesystem
        """
        self.base_path = Path(base_path)
        
        # Initialize storage components with shared filesystem kwargs
        fs_kwargs = {}
        
        # Initialize storage components
        self.queue = AsyncMemoryQueue(base_dir=str(self.base_path / "queues"), fs_kwargs=fs_kwargs)
        self.result_storage = AsyncMemoryResultStorage(base_dir=str(self.base_path / "results"), fs_kwargs=fs_kwargs)
        self.event_storage = AsyncMemoryEventStorage(base_dir=str(self.base_path / "events"), fs_kwargs=fs_kwargs)
        self.schedule_storage = AsyncMemoryScheduleStorage(base_dir=str(self.base_path / "schedules"), fs_kwargs=fs_kwargs)
        
        # Sync wrappers - these will share the same filesystem instances
        self.queue_sync = MemoryQueue(base_dir=str(self.base_path / "queues"), fs_kwargs=fs_kwargs)
        self.result_storage_sync = MemoryResultStorage(base_dir=str(self.base_path / "results"), fs_kwargs=fs_kwargs)
        self.event_storage_sync = MemoryEventStorage(base_dir=str(self.base_path / "events"), fs_kwargs=fs_kwargs)
        self.schedule_storage_sync = MemoryScheduleStorage(base_dir=str(self.base_path / "schedules"), fs_kwargs=fs_kwargs)
    
    async def connect(self) -> None:
        """Connect all storage components."""
        # Create a shared filesystem instance
        shared_fs = fsspec.filesystem("memory")
        
        # Connect async components with shared filesystem
        await self.queue.connect()
        await self.result_storage.connect()
        await self.event_storage.connect()
        await self.schedule_storage.connect()
        
        # Share the filesystem instance with sync components
        self.queue_sync._fs = self.queue._fs
        self.result_storage_sync._fs = self.result_storage._fs
        self.event_storage_sync._fs = self.event_storage._fs
        self.schedule_storage_sync._fs = self.schedule_storage._fs
    
    async def disconnect(self) -> None:
        """Disconnect all storage components."""
        await self.queue.disconnect()
        await self.result_storage.disconnect()
        await self.event_storage.disconnect()
        await self.schedule_storage.disconnect()
    
    def connect_sync(self) -> None:
        """Connect all storage components (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect all storage components (sync)."""
        asyncio.run(self.disconnect())
    
    async def cleanup(self) -> None:
        """Clean up expired data across all storage components."""
        # Clean up expired tasks
        await self.queue.cleanup_expired_tasks()
        
        # Clean up expired results
        await self.result_storage.cleanup_expired_results()
        
        # Clean up old events (older than 7 days)
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        await self.event_storage.cleanup_old_events(cutoff_time)
    
    def cleanup_sync(self) -> None:
        """Clean up expired data across all storage components (sync)."""
        asyncio.run(self.cleanup())
    
    def get_config(self) -> dict:
        """Get backend configuration."""
        return {
            "type": "memory",
            "base_path": str(self.base_path),
            "description": "In-memory storage backend using fsspec MemoryFileSystem"
        }