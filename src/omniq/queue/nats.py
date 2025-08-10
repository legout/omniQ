"""NATS queue implementations for OmniQ.

This module provides concrete NATS-based implementations of the queue interface:
- AsyncNATSQueue and NATSQueue: Task queue using nats.aio

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import anyio
import nats.aio.client

from .base import BaseQueue
from ..models.task import Task
from .. import json


class AsyncNATSQueue(BaseQueue):
    """Async NATS-based task queue implementation.

    Features:
    - Multiple named queues support using subject prefixes
    - Distributed messaging with NATS
    - Queue groups for exclusive consumption
    - Persistent storage with JetStream (if available)
    """

    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        subject_prefix: str = "omniq",
        queue_group: str = "omniq_workers",
        **connection_kwargs,
    ):
        """Initialize the async NATS queue.

        Args:
            nats_url: NATS connection URL
            subject_prefix: Prefix for all NATS subjects
            queue_group: NATS queue group for exclusive consumption
            **connection_kwargs: Additional connection arguments for NATS
        """
        self.nats_url = nats_url
        self.subject_prefix = subject_prefix
        self.queue_group = queue_group
        self.connection_kwargs = connection_kwargs
        self.nc: Optional[nats.aio.client.Client] = None
        self.js: Optional[nats.aio.client.JetStream] = None
        self._initialized = False
        self._pending_tasks: Dict[str, Task] = {}
        self._locks: Dict[uuid.UUID, asyncio.Lock] = {}

    async def _ensure_initialized(self):
        """Ensure the NATS connection is initialized."""
        if self._initialized:
            return

        # Create NATS connection
        self.nc = await nats.aio.client.connect(self.nats_url, **self.connection_kwargs)

        # Try to get JetStream context
        try:
            self.js = self.nc.jetstream()
        except Exception:
            # JetStream not available, will use basic NATS
            pass

        self._initialized = True

    def _get_subject(self, queue_name: str) -> str:
        """Get the NATS subject for a specific queue."""
        return f"{self.subject_prefix}.queue.{queue_name}"

    def _get_result_subject(self, task_id: uuid.UUID) -> str:
        """Get the NATS subject for task results."""
        return f"{self.subject_prefix}.result.{task_id}"

    def _get_lock_subject(self, task_id: uuid.UUID) -> str:
        """Get the NATS subject for task locks."""
        return f"{self.subject_prefix}.lock.{task_id}"

    async def _acquire_lock(
        self,
        task_id: uuid.UUID,
        lock_timeout: Optional[timedelta] = None,
        worker_id: str = "worker",
    ) -> bool:
        """Acquire a lock for a task using NATS messaging.

        Args:
            task_id: ID of the task to lock
            lock_timeout: How long to hold the lock
            worker_id: Identifier for the worker acquiring the lock

        Returns:
            True if lock was acquired, False otherwise
        """
        if task_id not in self._locks:
            self._locks[task_id] = asyncio.Lock()

        # Try to acquire the asyncio lock
        if lock_timeout:
            try:
                await asyncio.wait_for(
                    self._locks[task_id].acquire(), timeout=lock_timeout.total_seconds()
                )
                return True
            except asyncio.TimeoutError:
                return False
        else:
            return await self._locks[task_id].acquire()

    async def _release_lock(self, task_id: uuid.UUID) -> None:
        """Release a lock for a task.

        Args:
            task_id: ID of the task to unlock
        """
        if task_id in self._locks and self._locks[task_id].locked():
            self._locks[task_id].release()

    async def enqueue_async(self, task: Task, queue_name: str = "default") -> None:
        """Enqueue a task asynchronously."""
        await self._ensure_initialized()

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

        subject = self._get_subject(queue_name)

        if self.js:
            # Use JetStream for persistent messaging
            try:
                await self.js.publish(subject, json.dumps(task_data).encode())
            except Exception:
                # Fall back to basic NATS
                await self.nc.publish(subject, json.dumps(task_data).encode())
        else:
            # Use basic NATS
            await self.nc.publish(subject, json.dumps(task_data).encode())

    async def dequeue_async(
        self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None
    ) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()

        subject = self._get_subject(queue_name)

        # Create a subscription for this queue
        if self.js:
            # Use JetStream for persistent messaging
            try:
                sub = await self.js.subscribe(subject, queue=self.queue_group)
            except Exception:
                # Fall back to basic NATS
                sub = await self.nc.subscribe(subject, queue=self.queue_group)
        else:
            # Use basic NATS
            sub = await self.nc.subscribe(subject, queue=self.queue_group)

        try:
            # Wait for a message with timeout
            timeout = 5.0  # Default timeout
            if lock_timeout:
                timeout = min(lock_timeout.total_seconds(), 30.0)  # Cap at 30 seconds

            msg = await sub.next_msg(timeout=timeout)

            if msg:
                # Parse task data
                task_data = json.loads(msg.data.decode())
                task_id = uuid.UUID(task_data["id"])

                # Try to acquire lock
                if await self._acquire_lock(task_id, lock_timeout):
                    # Reconstruct the task
                    task = Task(
                        id=task_id,
                        func_name=task_data["func_name"],
                        args=tuple(task_data["args"]),
                        kwargs=task_data["kwargs"],
                        created_at=datetime.fromisoformat(task_data["created_at"]),
                        ttl=timedelta(seconds=task_data["ttl_seconds"])
                        if task_data["ttl_seconds"]
                        else None,
                    )

                    # Store task for later completion/release
                    self._pending_tasks[str(task_id)] = task

                    return task

            return None
        except asyncio.TimeoutError:
            return None
        finally:
            # Clean up subscription
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()

        # Remove from pending tasks
        task_id_str = str(task_id)
        if task_id_str in self._pending_tasks:
            del self._pending_tasks[task_id_str]

        # Release lock
        await self._release_lock(task_id)

    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()

        # Release lock
        await self._release_lock(task_id)

    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue.

        Note: NATS doesn't provide a direct way to get queue size.
        This is an approximation based on pending tasks.
        """
        await self._ensure_initialized()

        # This is an approximation since NATS doesn't provide queue size
        # In a real implementation, you might need to track this separately
        return len(self._pending_tasks)

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
            # Check all pending tasks for expiration
            expired_task_ids = []

            for task_id_str, task in self._pending_tasks.items():
                # Check if task has TTL and is expired
                if task.ttl:
                    expiry_time = task.created_at + task.ttl

                    if now > expiry_time:
                        expired_task_ids.append(task_id_str)

            # Remove expired tasks
            for task_id_str in expired_task_ids:
                task_id = uuid.UUID(task_id_str)
                await self._release_lock(task_id)
                del self._pending_tasks[task_id_str]
                cleaned_count += 1

            return cleaned_count

        except Exception:
            return 0

    async def list_queues_async(self) -> List[str]:
        """List all available queue names.

        Note: NATS doesn't provide a direct way to list queues.
        This returns a default list.
        """
        await self._ensure_initialized()

        # NATS doesn't provide a way to list queues
        # In a real implementation, you might need to track this separately
        return ["default"]

    async def close_async(self) -> None:
        """Close the NATS connection."""
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
            self._initialized = False
            self._pending_tasks.clear()
            self._locks.clear()


class NATSQueue(AsyncNATSQueue):
    """Synchronous wrapper for AsyncNATSQueue."""

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

    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        anyio.run(self.close_async)

    def cleanup_expired_tasks(self, queue_name: Optional[str] = None) -> int:
        """Synchronous wrapper for cleanup_expired_tasks_async."""
        return anyio.run(self.cleanup_expired_tasks_async, queue_name)

    def __enter__(self):
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()


# Alias for consistency with other queue implementations
AsyncNatsQueue = AsyncNATSQueue
NatsQueue = NATSQueue
