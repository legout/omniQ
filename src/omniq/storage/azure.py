"""
Azure Blob Storage implementation for OmniQ using fsspec and adlfs.

This module provides Azure Blob Storage-based implementations for task queue,
result storage, event storage, and schedule storage using fsspec
with AzureBlobFileSystem for cloud-based operations.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import fsspec
import msgspec

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent
from ..models.schedule import Schedule, ScheduleStatus


class AsyncAzureQueue(BaseTaskQueue):
    """
    Async Azure Blob Storage-based task queue implementation using fsspec and adlfs.
    
    This class implements the BaseTaskQueue interface using fsspec
    with AzureBlobFileSystem for persistent task storage with support for
    multiple queues organized in Azure container structure.
    """
    
    def __init__(
        self,
        container_name: str,
        base_prefix: str = "omniq",
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        azure_additional_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the Azure Blob Storage-based task queue.
        
        Args:
            container_name: Azure container name for storing task files
            base_prefix: Base prefix/path within the container
            connection_string: Azure storage connection string
            account_name: Azure storage account name
            account_key: Azure storage account key
            sas_token: Azure SAS token
            tenant_id: Azure tenant ID (for service principal auth)
            client_id: Azure client ID (for service principal auth)
            client_secret: Azure client secret (for service principal auth)
            azure_additional_kwargs: Additional kwargs for adlfs
        """
        self.container_name = container_name
        self.base_prefix = base_prefix.strip("/")
        
        # Azure configuration
        self.azure_kwargs = azure_additional_kwargs or {}
        if connection_string:
            self.azure_kwargs["connection_string"] = connection_string
        if account_name:
            self.azure_kwargs["account_name"] = account_name
        if account_key:
            self.azure_kwargs["account_key"] = account_key
        if sas_token:
            self.azure_kwargs["sas_token"] = sas_token
        if tenant_id:
            self.azure_kwargs["tenant_id"] = tenant_id
        if client_id:
            self.azure_kwargs["client_id"] = client_id
        if client_secret:
            self.azure_kwargs["client_secret"] = client_secret
        
        self._fs: Optional[fsspec.AbstractFileSystem] = None
        
        # Azure path structure
        self.tasks_prefix = f"{self.base_prefix}/tasks"
        self.queues_prefix = f"{self.base_prefix}/queues"
    
    async def connect(self) -> None:
        """Connect to Azure Blob Storage."""
        if self._fs is not None:
            return
        
        try:
            # Import adlfs here to provide better error messages
            import adlfs
        except ImportError:
            raise ImportError(
                "adlfs is required for Azure storage. Install it with: pip install adlfs"
            )
        
        # Create Azure filesystem instance
        self._fs = fsspec.filesystem("abfs", **self.azure_kwargs)
        
        # Ensure container exists (if we have permissions)
        try:
            if self._fs and not self._fs.exists(self.container_name):
                self._fs.makedirs(self.container_name, exist_ok=True)
        except Exception:
            # Container might exist but we don't have list permissions
            pass
    
    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage."""
        self._fs = None
    
    def _get_task_path(self, task_id: str) -> str:
        """Get the Azure path for a task."""
        return f"{self.container_name}/{self.tasks_prefix}/{task_id}.json"
    
    def _get_queue_path(self, queue_name: str) -> str:
        """Get the Azure prefix for a queue."""
        return f"{self.container_name}/{self.queues_prefix}/{queue_name}"
    
    def _get_queue_task_path(self, queue_name: str, task_id: str) -> str:
        """Get the Azure path for a task in a queue."""
        return f"{self.container_name}/{self.queues_prefix}/{queue_name}/{task_id}.json"
    
    async def _write_task_file(self, task: Task) -> None:
        """Write task data to Azure Blob Storage."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
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
        """Read task data from Azure Blob Storage."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
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
        """Create a queue reference for the task."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        queue_task_path = self._get_queue_task_path(task.queue_name, task.id)
        
        # For Azure, we create a reference file that points to the main task
        reference_data = {
            "task_id": task.id,
            "task_path": self._get_task_path(task.id),
            "priority": task.priority,
            "created_at": task.created_at.isoformat(),
            "run_at": task.run_at.isoformat() if task.run_at else None,
        }
        
        with self._fs.open(queue_task_path, "w") as f:
            json.dump(reference_data, f)
    
    async def _remove_queue_link(self, task_id: str, queue_name: str) -> None:
        """Remove a queue reference for the task."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        queue_task_path = self._get_queue_task_path(queue_name, task_id)
        if self._fs.exists(queue_task_path):
            self._fs.rm(queue_task_path)
    
    async def enqueue(self, task: Task) -> str:
        """Enqueue a task for processing."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        # Write task file
        await self._write_task_file(task)
        
        # Create queue reference
        await self._create_queue_link(task)
        
        return task.id
    
    async def dequeue(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task from the specified queues."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        # Collect all pending tasks from specified queues
        pending_tasks = []
        
        for queue_name in queues:
            queue_prefix = self._get_queue_path(queue_name)
            
            try:
                # List all task references in the queue
                task_files = self._fs.ls(queue_prefix)
                for task_file in task_files:
                    if task_file.endswith('.json'):
                        try:
                            with self._fs.open(task_file, "r") as f:
                                ref_data = json.load(f)
                            
                            task_id = ref_data["task_id"]
                            task = await self._read_task_file(task_id)
                            
                            if task and task.status == TaskStatus.PENDING:
                                # Check if task is ready to run
                                now = datetime.utcnow()
                                if task.run_at and task.run_at > now:
                                    continue
                                if task.expires_at and task.expires_at <= now:
                                    continue
                                
                                pending_tasks.append((task, queue_name))
                        except (json.JSONDecodeError, KeyError):
                            continue
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
            raise RuntimeError("Azure filesystem not connected")
        
        # Write updated task file
        await self._write_task_file(task)
        
        # If task is pending, ensure queue reference exists
        if task.status == TaskStatus.PENDING:
            await self._create_queue_link(task)
        else:
            # Remove from queue if not pending
            await self._remove_queue_link(task.id, task.queue_name)
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task from the queue."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        task = await self._read_task_file(task_id)
        if task is None:
            return False
        
        # Remove queue reference
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
            raise RuntimeError("Azure filesystem not connected")
        
        tasks = []
        
        if queue_name:
            # List tasks from specific queue
            queue_prefix = self._get_queue_path(queue_name)
            try:
                task_files = self._fs.ls(queue_prefix)
                for task_file in task_files:
                    if task_file.endswith('.json'):
                        try:
                            with self._fs.open(task_file, "r") as f:
                                ref_data = json.load(f)
                            
                            task_id = ref_data["task_id"]
                            task = await self._read_task_file(task_id)
                            if task:
                                tasks.append(task)
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                pass
        else:
            # List all tasks
            tasks_prefix = f"{self.container_name}/{self.tasks_prefix}"
            try:
                task_files = self._fs.ls(tasks_prefix)
                for task_file in task_files:
                    if task_file.endswith('.json'):
                        task_id = Path(task_file).stem
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
            raise RuntimeError("Azure filesystem not connected")
        
        queue_prefix = self._get_queue_path(queue_name)
        
        try:
            task_files = self._fs.ls(queue_prefix)
            return len([f for f in task_files if f.endswith('.json')])
        except Exception:
            return 0
    
    async def cleanup_expired_tasks(self) -> int:
        """Clean up expired tasks."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        cleaned_count = 0
        now = datetime.utcnow()
        
        tasks_prefix = f"{self.container_name}/{self.tasks_prefix}"
        
        try:
            task_files = self._fs.ls(tasks_prefix)
            for task_file in task_files:
                if task_file.endswith('.json'):
                    task_id = Path(task_file).stem
                    task = await self._read_task_file(task_id)
                    
                    if task and task.expires_at and task.expires_at <= now:
                        await self.delete_task(task_id)
                        cleaned_count += 1
        except Exception:
            pass
        
        return cleaned_count


class AzureQueue(AsyncAzureQueue):
    """
    Synchronous wrapper around AsyncAzureQueue.
    
    This class provides a synchronous interface to the async Azure queue
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Azure Blob Storage (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Azure Blob Storage (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, create a task instead
            if loop.is_running():
                # Just set _fs to None directly since disconnect() only does that
                self._fs = None
                return
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            pass
        
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


class AsyncAzureResultStorage(BaseResultStorage):
    """
    Async Azure Blob Storage-based result storage implementation using fsspec and adlfs.
    
    This class implements the BaseResultStorage interface using fsspec
    for persistent result storage in Azure Blob Storage.
    """
    
    def __init__(
        self,
        container_name: str,
        base_prefix: str = "omniq",
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        azure_additional_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the Azure Blob Storage-based result storage.
        
        Args:
            container_name: Azure container name for storing result files
            base_prefix: Base prefix/path within the container
            connection_string: Azure storage connection string
            account_name: Azure storage account name
            account_key: Azure storage account key
            sas_token: Azure SAS token
            tenant_id: Azure tenant ID (for service principal auth)
            client_id: Azure client ID (for service principal auth)
            client_secret: Azure client secret (for service principal auth)
            azure_additional_kwargs: Additional kwargs for adlfs
        """
        self.container_name = container_name
        self.base_prefix = base_prefix.strip("/")
        
        # Azure configuration
        self.azure_kwargs = azure_additional_kwargs or {}
        if connection_string:
            self.azure_kwargs["connection_string"] = connection_string
        if account_name:
            self.azure_kwargs["account_name"] = account_name
        if account_key:
            self.azure_kwargs["account_key"] = account_key
        if sas_token:
            self.azure_kwargs["sas_token"] = sas_token
        if tenant_id:
            self.azure_kwargs["tenant_id"] = tenant_id
        if client_id:
            self.azure_kwargs["client_id"] = client_id
        if client_secret:
            self.azure_kwargs["client_secret"] = client_secret
        
        self._fs: Optional[fsspec.AbstractFileSystem] = None
        
        # Azure path structure
        self.results_prefix = f"{self.base_prefix}/results"
    
    async def connect(self) -> None:
        """Connect to Azure Blob Storage."""
        if self._fs is not None:
            return
        
        try:
            # Import adlfs here to provide better error messages
            import adlfs
        except ImportError:
            raise ImportError(
                "adlfs is required for Azure storage. Install it with: pip install adlfs"
            )
        
        # Create Azure filesystem instance
        self._fs = fsspec.filesystem("abfs", **self.azure_kwargs)
        
        # Ensure container exists (if we have permissions)
        try:
            if self._fs and not self._fs.exists(self.container_name):
                self._fs.makedirs(self.container_name, exist_ok=True)
        except Exception:
            # Container might exist but we don't have list permissions
            pass
    
    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage."""
        self._fs = None
    
    def _get_result_path(self, task_id: str) -> str:
        """Get the Azure path for a result."""
        return f"{self.container_name}/{self.results_prefix}/{task_id}.json"
    
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
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
            raise RuntimeError("Azure filesystem not connected")
        
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
            raise RuntimeError("Azure filesystem not connected")
        
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
            raise RuntimeError("Azure filesystem not connected")
        
        results = []
        results_prefix = f"{self.container_name}/{self.results_prefix}"
        
        try:
            result_files = self._fs.ls(results_prefix)
            for result_file in result_files:
                if result_file.endswith('.json'):
                    task_id = Path(result_file).stem
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
            raise RuntimeError("Azure filesystem not connected")
        
        cleaned_count = 0
        now = datetime.utcnow()
        results_prefix = f"{self.container_name}/{self.results_prefix}"
        
        try:
            result_files = self._fs.ls(results_prefix)
            for result_file in result_files:
                if result_file.endswith('.json'):
                    task_id = Path(result_file).stem
                    result = await self.get(task_id)
                    
                    if result and result.expires_at and result.expires_at <= now:
                        await self.delete(task_id)
                        cleaned_count += 1
        except Exception:
            pass
        
        return cleaned_count


class AzureResultStorage(AsyncAzureResultStorage):
    """
    Synchronous wrapper around AsyncAzureResultStorage.
    
    This class provides a synchronous interface to the async Azure result storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Azure Blob Storage (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Azure Blob Storage (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, create a task instead
            if loop.is_running():
                # Just set _fs to None directly since disconnect() only does that
                self._fs = None
                return
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            pass
        
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


class AsyncAzureEventStorage(BaseEventStorage):
    """
    Async Azure Blob Storage-based event storage implementation using fsspec and adlfs.
    
    This class implements the BaseEventStorage interface using fsspec
    for persistent event logging as JSON files in Azure Blob Storage.
    """
    
    def __init__(
        self,
        container_name: str,
        base_prefix: str = "omniq",
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        azure_additional_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the Azure Blob Storage-based event storage.
        
        Args:
            container_name: Azure container name for storing event files
            base_prefix: Base prefix/path within the container
            connection_string: Azure storage connection string
            account_name: Azure storage account name
            account_key: Azure storage account key
            sas_token: Azure SAS token
            tenant_id: Azure tenant ID (for service principal auth)
            client_id: Azure client ID (for service principal auth)
            client_secret: Azure client secret (for service principal auth)
            azure_additional_kwargs: Additional kwargs for adlfs
        """
        self.container_name = container_name
        self.base_prefix = base_prefix.strip("/")
        
        # Azure configuration
        self.azure_kwargs = azure_additional_kwargs or {}
        if connection_string:
            self.azure_kwargs["connection_string"] = connection_string
        if account_name:
            self.azure_kwargs["account_name"] = account_name
        if account_key:
            self.azure_kwargs["account_key"] = account_key
        if sas_token:
            self.azure_kwargs["sas_token"] = sas_token
        if tenant_id:
            self.azure_kwargs["tenant_id"] = tenant_id
        if client_id:
            self.azure_kwargs["client_id"] = client_id
        if client_secret:
            self.azure_kwargs["client_secret"] = client_secret
        
        self._fs: Optional[fsspec.AbstractFileSystem] = None
        
        # Azure path structure
        self.events_prefix = f"{self.base_prefix}/events"
    
    async def connect(self) -> None:
        """Connect to Azure Blob Storage."""
        if self._fs is not None:
            return
        
        try:
            # Import adlfs here to provide better error messages
            import adlfs
        except ImportError:
            raise ImportError(
                "adlfs is required for Azure storage. Install it with: pip install adlfs"
            )
        
        # Create Azure filesystem instance
        self._fs = fsspec.filesystem("abfs", **self.azure_kwargs)
        
        # Ensure container exists (if we have permissions)
        try:
            if self._fs and not self._fs.exists(self.container_name):
                self._fs.makedirs(self.container_name, exist_ok=True)
        except Exception:
            # Container might exist but we don't have list permissions
            pass
    
    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage."""
        self._fs = None
    
    def _get_event_path(self, event_id: str) -> str:
        """Get the Azure path for an event."""
        return f"{self.container_name}/{self.events_prefix}/{event_id}.json"
    
    async def log_event(self, event: TaskEvent) -> None:
        """Log a task event."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
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
            raise RuntimeError("Azure filesystem not connected")
        
        events = []
        events_prefix = f"{self.container_name}/{self.events_prefix}"
        
        try:
            event_files = self._fs.ls(events_prefix)
            for event_file in event_files:
                if event_file.endswith('.json'):
                    try:
                        with self._fs.open(event_file, "r") as f:
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
            raise RuntimeError("Azure filesystem not connected")
        
        cleaned_count = 0
        events_prefix = f"{self.container_name}/{self.events_prefix}"
        
        try:
            event_files = self._fs.ls(events_prefix)
            for event_file in event_files:
                if event_file.endswith('.json'):
                    try:
                        with self._fs.open(event_file, "r") as f:
                            event_data = json.load(f)
                        
                        event = msgspec.json.decode(event_data["event_data"], type=TaskEvent)
                        
                        if event.timestamp < older_than:
                            self._fs.rm(event_file)
                            cleaned_count += 1
                    except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
                        continue
        except Exception:
            pass
        
        return cleaned_count


class AzureEventStorage(AsyncAzureEventStorage):
    """
    Synchronous wrapper around AsyncAzureEventStorage.
    
    This class provides a synchronous interface to the async Azure event storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Azure Blob Storage (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Azure Blob Storage (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, create a task instead
            if loop.is_running():
                # Just set _fs to None directly since disconnect() only does that
                self._fs = None
                return
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            pass
        
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


class AsyncAzureScheduleStorage(BaseScheduleStorage):
    """
    Async Azure Blob Storage-based schedule storage implementation using fsspec and adlfs.
    
    This class implements the BaseScheduleStorage interface using fsspec
    for persistent schedule storage and management in Azure Blob Storage.
    """
    
    def __init__(
        self,
        container_name: str,
        base_prefix: str = "omniq",
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        azure_additional_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the Azure Blob Storage-based schedule storage.
        
        Args:
            container_name: Azure container name for storing schedule files
            base_prefix: Base prefix/path within the container
            connection_string: Azure storage connection string
            account_name: Azure storage account name
            account_key: Azure storage account key
            sas_token: Azure SAS token
            tenant_id: Azure tenant ID (for service principal auth)
            client_id: Azure client ID (for service principal auth)
            client_secret: Azure client secret (for service principal auth)
            azure_additional_kwargs: Additional kwargs for adlfs
        """
        self.container_name = container_name
        self.base_prefix = base_prefix.strip("/")
        
        # Azure configuration
        self.azure_kwargs = azure_additional_kwargs or {}
        if connection_string:
            self.azure_kwargs["connection_string"] = connection_string
        if account_name:
            self.azure_kwargs["account_name"] = account_name
        if account_key:
            self.azure_kwargs["account_key"] = account_key
        if sas_token:
            self.azure_kwargs["sas_token"] = sas_token
        if tenant_id:
            self.azure_kwargs["tenant_id"] = tenant_id
        if client_id:
            self.azure_kwargs["client_id"] = client_id
        if client_secret:
            self.azure_kwargs["client_secret"] = client_secret
        
        self._fs: Optional[fsspec.AbstractFileSystem] = None
        
        # Azure path structure
        self.schedules_prefix = f"{self.base_prefix}/schedules"
    
    async def connect(self) -> None:
        """Connect to Azure Blob Storage."""
        if self._fs is not None:
            return
        
        try:
            # Import adlfs here to provide better error messages
            import adlfs
        except ImportError:
            raise ImportError(
                "adlfs is required for Azure storage. Install it with: pip install adlfs"
            )
        
        # Create Azure filesystem instance
        self._fs = fsspec.filesystem("abfs", **self.azure_kwargs)
        
        # Ensure container exists (if we have permissions)
        try:
            if self._fs and not self._fs.exists(self.container_name):
                self._fs.makedirs(self.container_name, exist_ok=True)
        except Exception:
            # Container might exist but we don't have list permissions
            pass
    
    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage."""
        self._fs = None
    
    def _get_schedule_path(self, schedule_id: str) -> str:
        """Get the Azure path for a schedule."""
        return f"{self.container_name}/{self.schedules_prefix}/{schedule_id}.json"
    
    async def save_schedule(self, schedule: Schedule) -> None:
        """Save a schedule."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
        schedule_path = self._get_schedule_path(schedule.id)
        schedule_data = {
            "schedule_data": msgspec.json.encode(schedule).decode(),
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
            raise RuntimeError("Azure filesystem not connected")
        
        schedule_path = self._get_schedule_path(schedule_id)
        
        if not self._fs.exists(schedule_path):
            return None
        
        try:
            with self._fs.open(schedule_path, "r") as f:
                schedule_data = json.load(f)
            
            return msgspec.json.decode(schedule_data["schedule_data"], type=Schedule)
        except (json.JSONDecodeError, KeyError, msgspec.DecodeError):
            return None
    
    async def update_schedule(self, schedule: Schedule) -> None:
        """Update a schedule."""
        await self.save_schedule(schedule)
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if self._fs is None:
            raise RuntimeError("Azure filesystem not connected")
        
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
            raise RuntimeError("Azure filesystem not connected")
        
        schedules = []
        schedules_prefix = f"{self.container_name}/{self.schedules_prefix}"
        
        try:
            schedule_files = self._fs.ls(schedules_prefix)
            for schedule_file in schedule_files:
                if schedule_file.endswith('.json'):
                    schedule_id = Path(schedule_file).stem
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
            raise RuntimeError("Azure filesystem not connected")
        
        ready_schedules = []
        now = datetime.utcnow()
        schedules_prefix = f"{self.container_name}/{self.schedules_prefix}"
        
        try:
            schedule_files = self._fs.ls(schedules_prefix)
            for schedule_file in schedule_files:
                if schedule_file.endswith('.json'):
                    schedule_id = Path(schedule_file).stem
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


class AzureScheduleStorage(AsyncAzureScheduleStorage):
    """
    Synchronous wrapper around AsyncAzureScheduleStorage.
    
    This class provides a synchronous interface to the async Azure schedule storage
    implementation using asyncio for execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Azure Blob Storage (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Azure Blob Storage (sync)."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in a running loop, create a task instead
            if loop.is_running():
                # Just set _fs to None directly since disconnect() only does that
                self._fs = None
                return
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            pass
        
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