"""Memory queue implementations for OmniQ.

This module provides concrete memory-based implementations of the queue interface:
- AsyncMemoryQueue and MemoryQueue: Task queue with locking mechanism using fsspec.MemoryFileSystem

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import anyio
from fsspec.implementations.memory import MemoryFileSystem

from .base import BaseQueue
from ..models.task import Task
from .. import json


class AsyncMemoryQueue(BaseQueue):
    """Async memory-based task queue implementation.

    Features:
    - Multiple named queues support using fsspec.MemoryFileSystem
    - Transactional task locking with in-memory locks
    - Volatile storage (data lost on restart)
    - Fast in-memory operations
    """

    def __init__(self):
        """Initialize the async memory queue."""
        self.fs = MemoryFileSystem()
        self._initialized = False
        self._locks: Dict[str, asyncio.Lock] = {}

    async def _ensure_initialized(self):
        """Ensure the filesystem and directories are initialized."""
        if self._initialized:
            return

        # Ensure queues directory exists
        self.fs.makedirs("queues", exist_ok=True)

        self._initialized = True

    def _get_queue_path(self, queue_name: str) -> str:
        """Get the path for a specific queue."""
        return f"queues/{queue_name}"

    def _get_task_path(self, queue_name: str, task_id: uuid.UUID) -> str:
        """Get the path for a specific task."""
        return f"queues/{queue_name}/{task_id}.json"

    def _get_lock_path(self, queue_name: str, task_id: uuid.UUID) -> str:
        """Get the path for a task lock file."""
        return f"queues/{queue_name}/{task_id}.lock"

    async def _acquire_lock(
        self,
        queue_name: str,
        task_id: uuid.UUID,
        lock_timeout: Optional[timedelta] = None,
    ) -> bool:
        """Acquire a lock for a task."""
        lock_key = f"{queue_name}:{task_id}"

        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()

        # Try to acquire the asyncio lock
        if not self._locks[lock_key].locked():
            await self._locks[lock_key].acquire()

            # Create lock file with timeout info
            lock_path = self._get_lock_path(queue_name, task_id)
            lock_data = {
                "locked_at": datetime.utcnow().isoformat(),
                "lock_timeout_seconds": int(lock_timeout.total_seconds())
                if lock_timeout
                else None,
            }

            try:
                with self.fs.open(lock_path, "w") as f:
                    json.dump(lock_data, f)
                return True
            except Exception:
                self._locks[lock_key].release()
                return False

        return False

    async def _release_lock(self, queue_name: str, task_id: uuid.UUID) -> None:
        """Release a lock for a task."""
        lock_key = f"{queue_name}:{task_id}"

        # Remove lock file
        lock_path = self._get_lock_path(queue_name, task_id)
        try:
            self.fs.rm(lock_path)
        except FileNotFoundError:
            pass

        # Release asyncio lock
        if lock_key in self._locks and self._locks[lock_key].locked():
            self._locks[lock_key].release()

    async def _cleanup_expired_locks(self, queue_name: str) -> None:
        """Clean up expired locks."""
        queue_path = self._get_queue_path(queue_name)

        try:
            for lock_file in self.fs.glob(f"{queue_path}/*.lock"):
                try:
                    with self.fs.open(lock_file, "r") as f:
                        lock_data = json.load(f)

                    locked_at = datetime.fromisoformat(lock_data["locked_at"])
                    lock_timeout_seconds = lock_data.get("lock_timeout_seconds")

                    if lock_timeout_seconds:
                        expired_time = locked_at + timedelta(
                            seconds=lock_timeout_seconds
                        )
                        if datetime.utcnow() > expired_time:
                            self.fs.rm(lock_file)
                            # Also release asyncio lock if it exists
                            task_id_str = lock_file.split("/")[-1].replace(".lock", "")
                            lock_key = f"{queue_name}:{task_id_str}"
                            if (
                                lock_key in self._locks
                                and self._locks[lock_key].locked()
                            ):
                                self._locks[lock_key].release()
                except Exception:
                    # Skip corrupted lock files
                    continue
        except Exception:
            # Skip if queue directory doesn't exist
            pass

    async def enqueue_async(self, task: Task, queue_name: str = "default") -> None:
        """Enqueue a task asynchronously."""
        await self._ensure_initialized()

        queue_path = self._get_queue_path(queue_name)
        task_path = self._get_task_path(queue_name, task.id)

        # Ensure queue directory exists
        self.fs.makedirs(queue_path, exist_ok=True)

        # Serialize task data
        task_data = {
            "id": str(task.id),
            "func_name": task.func_name,
            "args": task.args,
            "kwargs": task.kwargs,
            "created_at": task.created_at.isoformat(),
            "ttl_seconds": int(task.ttl.total_seconds()) if task.ttl else None,
            "status": "pending",
        }

        # Write task file
        with self.fs.open(task_path, "w") as f:
            json.dump(task_data, f)

    async def dequeue_async(
        self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None
    ) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()

        queue_path = self._get_queue_path(queue_name)

        # Clean up expired locks first
        await self._cleanup_expired_locks(queue_name)

        try:
            # List all task files (excluding lock files)
            task_files = [
                f
                for f in self.fs.glob(f"{queue_path}/*.json")
                if not f.endswith(".lock")
            ]

            if not task_files:
                return None

            # Sort by creation time (oldest first)
            task_files.sort(key=lambda f: self.fs.info(f)["created"])

            for task_file in task_files:
                try:
                    # Read task data
                    with self.fs.open(task_file, "r") as f:
                        task_data = json.load(f)

                    # Check if task is still pending
                    if task_data.get("status") != "pending":
                        continue

                    # Try to acquire lock
                    task_id = uuid.UUID(task_data["id"])
                    if await self._acquire_lock(queue_name, task_id, lock_timeout):
                        # Update task status to processing
                        task_data["status"] = "processing"
                        with self.fs.open(task_file, "w") as f:
                            json.dump(task_data, f)

                        # Reconstruct the task
                        return Task(
                            id=task_id,
                            func_name=task_data["func_name"],
                            args=tuple(task_data["args"]),
                            kwargs=task_data["kwargs"],
                            created_at=datetime.fromisoformat(task_data["created_at"]),
                            ttl=timedelta(seconds=task_data["ttl_seconds"])
                            if task_data["ttl_seconds"]
                            else None,
                        )
                except Exception:
                    # Skip corrupted task files
                    continue

            return None

        except Exception:
            # Queue directory doesn't exist or other error
            return None

    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()

        # Find and remove the task file
        try:
            for queue_file in self.fs.glob("queues/*/*.json"):
                if not queue_file.endswith(".lock"):
                    try:
                        with self.fs.open(queue_file, "r") as f:
                            task_data = json.load(f)

                        if uuid.UUID(task_data["id"]) == task_id:
                            self.fs.rm(queue_file)
                            await self._release_lock(queue_file.split("/")[-2], task_id)
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()

        # Find and update the task file
        try:
            for queue_file in self.fs.glob("queues/*/*.json"):
                if not queue_file.endswith(".lock"):
                    try:
                        with self.fs.open(queue_file, "r") as f:
                            task_data = json.load(f)

                        if uuid.UUID(task_data["id"]) == task_id:
                            # Update status back to pending
                            task_data["status"] = "pending"
                            with self.fs.open(queue_file, "w") as f:
                                json.dump(task_data, f)

                            # Release lock
                            await self._release_lock(queue_file.split("/")[-2], task_id)
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        await self._ensure_initialized()

        queue_path = self._get_queue_path(queue_name)

        try:
            # Count pending task files
            count = 0
            for task_file in self.fs.glob(f"{queue_path}/*.json"):
                if not task_file.endswith(".lock"):
                    try:
                        with self.fs.open(task_file, "r") as f:
                            task_data = json.load(f)

                        if task_data.get("status") == "pending":
                            count += 1
                    except Exception:
                        continue

            return count
        except Exception:
            return 0

    async def cleanup_expired_tasks_async(
        self, queue_name: Optional[str] = None
    ) -> int:
        """Clean up expired tasks from the queue.

        Args:
            queue_name: Specific queue to clean up, or None for all queues

        Returns:
            Number of expired tasks removed
        """
        await self._ensure_initialized()
        cleaned_count = 0
        now = datetime.utcnow()

        try:
            if queue_name:
                queue_names = [queue_name]
            else:
                queue_names = await self.list_queues_async()

            for q_name in queue_names:
                queue_path = self._get_queue_path(q_name)

                try:
                    for task_file in self.fs.glob(f"{queue_path}/*.json"):
                        if not task_file.endswith(".lock"):
                            try:
                                with self.fs.open(task_file, "r") as f:
                                    task_data = json.load(f)

                                # Check if task has TTL and is expired
                                ttl_seconds = task_data.get("ttl_seconds")
                                if ttl_seconds:
                                    created_at = datetime.fromisoformat(
                                        task_data["created_at"]
                                    )
                                    expiry_time = created_at + timedelta(
                                        seconds=ttl_seconds
                                    )

                                    if now > expiry_time:
                                        # Remove expired task
                                        self.fs.rm(task_file)
                                        task_id = uuid.UUID(task_data["id"])
                                        await self._release_lock(q_name, task_id)
                                        cleaned_count += 1
                            except Exception:
                                # Skip corrupted task files
                                continue
                except Exception:
                    # Skip if queue directory doesn't exist
                    continue

            return cleaned_count

        except Exception:
            return 0

    async def list_queues_async(self) -> List[str]:
        """List all available queue names."""
        await self._ensure_initialized()

        try:
            # List all directories in queues folder
            queue_dirs = self.fs.ls("queues", detail=False)
            return [
                q.split("/")[-1]
                for q in queue_dirs
                if self.fs.info(q)["type"] == "directory"
            ]
        except Exception:
            return []


class MemoryQueue(AsyncMemoryQueue):
    """Synchronous wrapper for AsyncMemoryQueue."""

    def enqueue(self, task: Task, queue_name: str = "default") -> None:
        """Synchronous wrapper for enqueue_async."""
        anyio.run(self.enqueue_async, task, queue_name)

    def dequeue(
        self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None
    ) -> Optional[Task]:
        """Synchronous wrapper for dequeue_async."""
        return anyio.run(self.dequeue_async, queue_name, lock_timeout)

    def complete_task(self, task_id: uuid.UUID) -> None:
        """Synchronous wrapper for complete_task_async."""
        anyio.run(self.complete_task_async, task_id)

    def release_task(self, task_id: uuid.UUID) -> None:
        """Synchronous wrapper for release_task_async."""
        anyio.run(self.release_task_async, task_id)

    def get_queue_size(self, queue_name: str = "default") -> int:
        """Synchronous wrapper for get_queue_size_async."""
        return anyio.run(self.get_queue_size_async, queue_name)

    def list_queues(self) -> List[str]:
        """Synchronous wrapper for list_queues_async."""
        return anyio.run(self.list_queues_async)

    def cleanup_expired_tasks(self, queue_name: Optional[str] = None) -> int:
        """Synchronous wrapper for cleanup_expired_tasks_async."""
        return anyio.run(self.cleanup_expired_tasks_async, queue_name)
