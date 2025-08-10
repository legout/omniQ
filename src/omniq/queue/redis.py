"""Redis queue implementations for OmniQ.

This module provides concrete Redis-based implementations of the queue interface:
- AsyncRedisQueue and RedisQueue: Task queue with locking mechanism using redis.asyncio

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import anyio
import redis.asyncio as redis

from .base import BaseQueue
from ..models.task import Task
from .. import json


class AsyncRedisQueue(BaseQueue):
    """Async Redis-based task queue implementation.

    Features:
    - Multiple named queues support using key prefixes
    - Transactional task locking with Redis atomic operations
    - Fast in-memory operations with Redis
    - Connection pooling for efficiency
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "omniq",
        max_connections: int = 10,
        **connection_kwargs,
    ):
        """Initialize the async Redis queue.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
            max_connections: Maximum number of connections in the pool
            **connection_kwargs: Additional connection arguments for redis
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs
        self.redis: Optional[redis.Redis] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the Redis connection is initialized."""
        if self._initialized:
            return

        # Create Redis connection pool
        self.redis = redis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            **self.connection_kwargs,
        )
        self.redis = redis.Redis(connection_pool=self.redis)

        # Test connection
        await self.redis.ping()

        self._initialized = True

    def _get_queue_key(self, queue_name: str) -> str:
        """Get the Redis key for a specific queue."""
        return f"{self.key_prefix}:queue:{queue_name}"

    def _get_task_key(self, task_id: uuid.UUID) -> str:
        """Get the Redis key for a specific task."""
        return f"{self.key_prefix}:task:{task_id}"

    def _get_lock_key(self, task_id: uuid.UUID) -> str:
        """Get the Redis key for a task lock."""
        return f"{self.key_prefix}:lock:{task_id}"

    def _get_queue_set_key(self) -> str:
        """Get the Redis key for the set of all queue names."""
        return f"{self.key_prefix}:queues"

    async def _acquire_lock(
        self,
        task_id: uuid.UUID,
        lock_timeout: Optional[timedelta] = None,
        worker_id: str = "worker",
    ) -> bool:
        """Acquire a lock for a task using Redis atomic operations.

        Args:
            task_id: ID of the task to lock
            lock_timeout: How long to hold the lock
            worker_id: Identifier for the worker acquiring the lock

        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = self._get_lock_key(task_id)
        lock_value = json.dumps(
            {
                "worker_id": worker_id,
                "locked_at": datetime.utcnow().isoformat(),
                "lock_timeout_seconds": int(lock_timeout.total_seconds())
                if lock_timeout
                else None,
            }
        )

        # Use SET with NX (only if not exists) and EX (expire)
        if lock_timeout:
            return await self.redis.set(lock_key, lock_value, nx=True, ex=lock_timeout)
        else:
            return await self.redis.set(lock_key, lock_value, nx=True)

    async def _release_lock(self, task_id: uuid.UUID) -> None:
        """Release a lock for a task.

        Args:
            task_id: ID of the task to unlock
        """
        lock_key = self._get_lock_key(task_id)
        await self.redis.delete(lock_key)

    async def _cleanup_expired_locks(self) -> None:
        """Clean up expired locks.

        Note: Redis automatically expires keys with TTL, so this is mainly
        for cleanup of locks without explicit TTL.
        """
        # This is handled automatically by Redis TTL
        pass

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

        # Use a pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            # Store task data
            task_key = self._get_task_key(task.id)
            await pipe.set(task_key, json.dumps(task_data))

            # Add task to queue (using a sorted set with timestamp as score)
            queue_key = self._get_queue_key(queue_name)
            timestamp = task.created_at.timestamp()
            await pipe.zadd(queue_key, {str(task.id): timestamp})

            # Add queue name to the set of all queues
            queues_set_key = self._get_queue_set_key()
            await pipe.sadd(queues_set_key, queue_name)

            # Execute pipeline
            await pipe.execute()

    async def dequeue_async(
        self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None
    ) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()

        queue_key = self._get_queue_key(queue_name)

        # Get the oldest task (lowest score)
        task_ids = await self.redis.zrange(queue_key, 0, 0)

        if not task_ids:
            return None

        task_id_str = task_ids[0]
        task_id = uuid.UUID(task_id_str)

        # Try to acquire lock
        if await self._acquire_lock(task_id, lock_timeout):
            # Get task data
            task_key = self._get_task_key(task_id)
            task_data_json = await self.redis.get(task_key)

            if not task_data_json:
                # Task data not found, release lock and clean up queue
                await self._release_lock(task_id)
                await self.redis.zrem(queue_key, task_id_str)
                return None

            task_data = json.loads(task_data_json)

            # Check if task is still pending
            if task_data.get("status") != "pending":
                # Task already being processed, release lock
                await self._release_lock(task_id)
                return None

            # Update task status to processing
            task_data["status"] = "processing"
            await self.redis.set(task_key, json.dumps(task_data))

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

        return None

    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()

        # Remove task data
        task_key = self._get_task_key(task_id)
        await self.redis.delete(task_key)

        # Remove task from all queues
        task_id_str = str(task_id)
        queues_set_key = self._get_queue_set_key()
        queue_names = await self.redis.smembers(queues_set_key)

        for queue_name in queue_names:
            queue_key = self._get_queue_key(queue_name.decode())
            await self.redis.zrem(queue_key, task_id_str)

        # Release lock
        await self._release_lock(task_id)

    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()

        # Get task data
        task_key = self._get_task_key(task_id)
        task_data_json = await self.redis.get(task_key)

        if task_data_json:
            task_data = json.loads(task_data_json)

            # Update task status back to pending
            task_data["status"] = "pending"
            await self.redis.set(task_key, json.dumps(task_data))

        # Release lock
        await self._release_lock(task_id)

    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        await self._ensure_initialized()

        queue_key = self._get_queue_key(queue_name)
        return await self.redis.zcard(queue_key)

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
                queue_key = self._get_queue_key(q_name)

                # Get all task IDs in the queue
                task_ids = await self.redis.zrange(queue_key, 0, -1)

                for task_id_str in task_ids:
                    try:
                        task_id = uuid.UUID(task_id_str)
                        task_key = self._get_task_key(task_id)

                        # Get task data
                        task_data_json = await self.redis.get(task_key)
                        if not task_data_json:
                            # Task data not found, clean up queue
                            await self.redis.zrem(queue_key, task_id_str)
                            continue

                        task_data = json.loads(task_data_json)

                        # Check if task has TTL and is expired
                        ttl_seconds = task_data.get("ttl_seconds")
                        if ttl_seconds:
                            created_at = datetime.fromisoformat(task_data["created_at"])
                            expiry_time = created_at + timedelta(seconds=ttl_seconds)

                            if now > expiry_time:
                                # Remove expired task
                                await self.redis.delete(task_key)
                                await self.redis.zrem(queue_key, task_id_str)
                                await self._release_lock(task_id)
                                cleaned_count += 1
                    except Exception:
                        # Skip corrupted task data
                        continue

            return cleaned_count

        except Exception:
            return 0

    async def list_queues_async(self) -> List[str]:
        """List all available queue names."""
        await self._ensure_initialized()

        queues_set_key = self._get_queue_set_key()
        queue_names = await self.redis.smembers(queues_set_key)
        return [queue_name.decode() for queue_name in queue_names]

    async def close_async(self) -> None:
        """Close the Redis connection pool."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._initialized = False


class RedisQueue(AsyncRedisQueue):
    """Synchronous wrapper for AsyncRedisQueue."""

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
