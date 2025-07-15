"""
Redis storage implementations for OmniQ.

This module provides Redis-based storage implementations for task queues,
result storage, event storage, and schedule storage using redis.asyncio
for async operations and synchronous wrappers.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import redis.asyncio as redis
import msgspec

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent
from ..models.schedule import Schedule


class AsyncRedisQueue(BaseTaskQueue):
    """
    Async Redis-based task queue implementation.
    
    This class implements the BaseTaskQueue interface using Redis
    for persistent task storage with support for multiple queues,
    priority ordering, and atomic operations.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        database: int = 0,
        password: Optional[str] = None,
        tasks_prefix: str = "omniq:tasks",
        max_connections: int = 10,
        socket_timeout: float = 30.0,
        socket_connect_timeout: float = 30.0,
        retry_on_timeout: bool = True,
        **redis_kwargs
    ):
        """
        Initialize Redis task queue.
        
        Args:
            host: Redis server host
            port: Redis server port
            database: Redis database number
            password: Redis password
            tasks_prefix: Key prefix for task storage
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            **redis_kwargs: Additional Redis connection parameters
        """
        self.host = host
        self.port = port
        self.database = database
        self.password = password
        self.tasks_prefix = tasks_prefix
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.redis_kwargs = redis_kwargs
        
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return
        
        self._redis = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.database,
            password=self.password,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            decode_responses=True,
            **self.redis_kwargs
        )
        
        # Test connection
        await self._redis.ping()
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis and self._connected:
            await self._redis.close()
            self._connected = False
    
    def _get_task_key(self, task_id: str) -> str:
        """Get Redis key for a task."""
        return f"{self.tasks_prefix}:task:{task_id}"
    
    def _get_queue_key(self, queue_name: str) -> str:
        """Get Redis key for a queue."""
        return f"{self.tasks_prefix}:queue:{queue_name}"
    
    def _get_lock_key(self, task_id: str) -> str:
        """Get Redis key for task lock."""
        return f"{self.tasks_prefix}:lock:{task_id}"
    
    async def enqueue(self, task: Task) -> str:
        """
        Enqueue a task for processing.
        
        Args:
            task: The task to enqueue
            
        Returns:
            The task ID
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        # Serialize task
        task_data = msgspec.json.encode(task).decode('utf-8')
        
        # Store task data
        task_key = self._get_task_key(task.id)
        await self._redis.set(task_key, task_data)
        
        # Add to queue with priority (higher priority = lower score for sorted set)
        queue_key = self._get_queue_key(task.queue_name)
        priority_score = -task.priority  # Negative for descending order
        await self._redis.zadd(queue_key, {task.id: priority_score})
        
        return task.id
    
    async def dequeue(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """
        Dequeue a task from the specified queues.
        
        Args:
            queues: List of queue names to check (in priority order)
            timeout: Maximum time to wait for a task (None = no timeout)
            
        Returns:
            The next available task or None if timeout reached
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        start_time = datetime.utcnow()
        
        while True:
            # Try each queue in priority order
            for queue_name in queues:
                queue_key = self._get_queue_key(queue_name)
                
                # Get highest priority task (lowest score)
                result = await self._redis.zrange(queue_key, 0, 0, withscores=True)
                
                if result:
                    task_id, score = result[0]
                    
                    # Try to acquire lock for this task
                    lock_key = self._get_lock_key(task_id)
                    lock_acquired = await self._redis.set(
                        lock_key, "locked", nx=True, ex=300  # 5 minute lock
                    )
                    
                    if lock_acquired:
                        # Remove from queue
                        await self._redis.zrem(queue_key, task_id)
                        
                        # Get task data
                        task_key = self._get_task_key(task_id)
                        task_data = await self._redis.get(task_key)
                        
                        if task_data:
                            try:
                                task = msgspec.json.decode(task_data.encode('utf-8'), type=Task)
                                
                                # Check if task is ready to run
                                if task.is_ready_to_run():
                                    # Update task status
                                    task.status = TaskStatus.RUNNING
                                    await self.update_task(task)
                                    return task
                                else:
                                    # Task not ready, release lock and continue
                                    await self._redis.delete(lock_key)
                                    continue
                            except Exception:
                                # Failed to deserialize, release lock
                                await self._redis.delete(lock_key)
                                continue
            
            # Check timeout
            if timeout is not None:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    return None
            
            # Wait before next attempt
            await asyncio.sleep(0.1)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task or None if not found
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        task_key = self._get_task_key(task_id)
        task_data = await self._redis.get(task_key)
        
        if task_data:
            try:
                return msgspec.json.decode(task_data.encode('utf-8'), type=Task)
            except Exception:
                return None
        
        return None
    
    async def update_task(self, task: Task) -> None:
        """
        Update a task in the queue.
        
        Args:
            task: The updated task
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        task_key = self._get_task_key(task.id)
        task_data = msgspec.json.encode(task).decode('utf-8')
        await self._redis.set(task_key, task_data)
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the queue.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if task was deleted, False if not found
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        task_key = self._get_task_key(task_id)
        lock_key = self._get_lock_key(task_id)
        
        # Delete task data and lock
        deleted_count = await self._redis.delete(task_key, lock_key)
        
        # Remove from all queues (we don't know which queue it was in)
        # This is inefficient but necessary for cleanup
        queue_pattern = f"{self.tasks_prefix}:queue:*"
        async for queue_key in self._redis.scan_iter(match=queue_pattern):
            await self._redis.zrem(queue_key, task_id)
        
        return deleted_count > 0
    
    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """
        List tasks in the queue.
        
        Args:
            queue_name: Filter by queue name
            status: Filter by task status
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            
        Returns:
            List of tasks
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        tasks = []
        
        if queue_name:
            # Get tasks from specific queue
            queue_key = self._get_queue_key(queue_name)
            task_ids = await self._redis.zrange(queue_key, 0, -1)
        else:
            # Get all task IDs
            task_pattern = f"{self.tasks_prefix}:task:*"
            task_ids = []
            async for task_key in self._redis.scan_iter(match=task_pattern):
                task_id = task_key.split(":")[-1]
                task_ids.append(task_id)
        
        # Fetch task data
        for task_id in task_ids[offset:]:
            if limit and len(tasks) >= limit:
                break
            
            task = await self.get_task(task_id)
            if task and (not status or task.status == status):
                tasks.append(task)
        
        return tasks
    
    async def get_queue_size(self, queue_name: str) -> int:
        """
        Get the number of tasks in a queue.
        
        Args:
            queue_name: The queue name
            
        Returns:
            Number of tasks in the queue
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        queue_key = self._get_queue_key(queue_name)
        return await self._redis.zcard(queue_key)
    
    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks.
        
        Returns:
            Number of tasks cleaned up
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        cleaned_count = 0
        now = datetime.utcnow()
        
        # Scan all tasks
        task_pattern = f"{self.tasks_prefix}:task:*"
        async for task_key in self._redis.scan_iter(match=task_pattern):
            task_data = await self._redis.get(task_key)
            if task_data:
                try:
                    task = msgspec.json.decode(task_data.encode('utf-8'), type=Task)
                    if task.is_expired():
                        task_id = task_key.split(":")[-1]
                        await self.delete_task(task_id)
                        cleaned_count += 1
                except Exception:
                    continue
        
        return cleaned_count


class RedisQueue(AsyncRedisQueue):
    """
    Synchronous wrapper around AsyncRedisQueue.
    
    This class provides a synchronous interface to the async Redis queue
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Redis (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Redis (sync)."""
        asyncio.run(self.disconnect())
    
    def enqueue_sync(self, task: Task) -> str:
        """Enqueue a task (sync)."""
        return asyncio.run(self.enqueue(task))
    
    def dequeue_sync(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task (sync)."""
        return asyncio.run(self.dequeue(queues, timeout))
    
    def get_task_sync(self, task_id: str) -> Optional[Task]:
        """Get a task by ID (sync)."""
        return asyncio.run(self.get_task(task_id))
    
    def update_task_sync(self, task: Task) -> None:
        """Update a task (sync)."""
        asyncio.run(self.update_task(task))
    
    def delete_task_sync(self, task_id: str) -> bool:
        """Delete a task (sync)."""
        return asyncio.run(self.delete_task(task_id))
    
    def list_tasks_sync(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """List tasks (sync)."""
        return asyncio.run(self.list_tasks(queue_name, status, limit, offset))
    
    def get_queue_size_sync(self, queue_name: str) -> int:
        """Get queue size (sync)."""
        return asyncio.run(self.get_queue_size(queue_name))
    
    def cleanup_expired_tasks_sync(self) -> int:
        """Clean up expired tasks (sync)."""
        return asyncio.run(self.cleanup_expired_tasks())
    
    # Sync context manager support
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncRedisResultStorage(BaseResultStorage):
    """
    Async Redis-based result storage implementation.
    
    This class implements the BaseResultStorage interface using Redis
    for persistent result storage with TTL support.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        database: int = 0,
        password: Optional[str] = None,
        results_prefix: str = "omniq:results",
        max_connections: int = 10,
        socket_timeout: float = 30.0,
        socket_connect_timeout: float = 30.0,
        retry_on_timeout: bool = True,
        **redis_kwargs
    ):
        """
        Initialize Redis result storage.
        
        Args:
            host: Redis server host
            port: Redis server port
            database: Redis database number
            password: Redis password
            results_prefix: Key prefix for result storage
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            **redis_kwargs: Additional Redis connection parameters
        """
        self.host = host
        self.port = port
        self.database = database
        self.password = password
        self.results_prefix = results_prefix
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.redis_kwargs = redis_kwargs
        
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return
        
        self._redis = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.database,
            password=self.password,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            decode_responses=True,
            **self.redis_kwargs
        )
        
        # Test connection
        await self._redis.ping()
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis and self._connected:
            await self._redis.close()
            self._connected = False
    
    def _get_result_key(self, task_id: str) -> str:
        """Get Redis key for a result."""
        return f"{self.results_prefix}:result:{task_id}"
    
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """
        Get a task result by task ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task result or None if not found
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        result_key = self._get_result_key(task_id)
        result_data = await self._redis.get(result_key)
        
        if result_data:
            try:
                return msgspec.json.decode(result_data.encode('utf-8'), type=TaskResult)
            except Exception:
                return None
        
        return None
    
    async def set(self, result: TaskResult) -> None:
        """
        Store a task result.
        
        Args:
            result: The task result to store
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        result_key = self._get_result_key(result.task_id)
        result_data = msgspec.json.encode(result).decode('utf-8')
        
        # Set with TTL if specified
        if result.ttl:
            ttl_seconds = int(result.ttl.total_seconds())
            await self._redis.setex(result_key, ttl_seconds, result_data)
        else:
            await self._redis.set(result_key, result_data)
    
    async def delete(self, task_id: str) -> bool:
        """
        Delete a task result.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if result was deleted, False if not found
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        result_key = self._get_result_key(task_id)
        deleted_count = await self._redis.delete(result_key)
        return deleted_count > 0
    
    async def list_results(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """
        List task results.
        
        Args:
            status: Filter by result status
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of task results
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        results = []
        
        # Scan all results
        result_pattern = f"{self.results_prefix}:result:*"
        result_keys = []
        async for result_key in self._redis.scan_iter(match=result_pattern):
            result_keys.append(result_key)
        
        # Fetch result data
        for result_key in result_keys[offset:]:
            if limit and len(results) >= limit:
                break
            
            result_data = await self._redis.get(result_key)
            if result_data:
                try:
                    result = msgspec.json.decode(result_data.encode('utf-8'), type=TaskResult)
                    if not status or result.status == status:
                        results.append(result)
                except Exception:
                    continue
        
        return results
    
    async def cleanup_expired_results(self) -> int:
        """
        Clean up expired results.
        
        Returns:
            Number of results cleaned up
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        cleaned_count = 0
        
        # Scan all results
        result_pattern = f"{self.results_prefix}:result:*"
        async for result_key in self._redis.scan_iter(match=result_pattern):
            result_data = await self._redis.get(result_key)
            if result_data:
                try:
                    result = msgspec.json.decode(result_data.encode('utf-8'), type=TaskResult)
                    if result.is_expired():
                        await self._redis.delete(result_key)
                        cleaned_count += 1
                except Exception:
                    continue
        
        return cleaned_count


class RedisResultStorage(AsyncRedisResultStorage):
    """
    Synchronous wrapper around AsyncRedisResultStorage.
    
    This class provides a synchronous interface to the async Redis result storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Redis (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Redis (sync)."""
        asyncio.run(self.disconnect())
    
    def get_sync(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result (sync)."""
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
    
    # Sync context manager support
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncRedisEventStorage(BaseEventStorage):
    """
    Async Redis-based event storage implementation.
    
    This class implements the BaseEventStorage interface using Redis
    for persistent event logging with time-based cleanup.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        database: int = 0,
        password: Optional[str] = None,
        events_prefix: str = "omniq:events",
        max_connections: int = 10,
        socket_timeout: float = 30.0,
        socket_connect_timeout: float = 30.0,
        retry_on_timeout: bool = True,
        **redis_kwargs
    ):
        """
        Initialize Redis event storage.
        
        Args:
            host: Redis server host
            port: Redis server port
            database: Redis database number
            password: Redis password
            events_prefix: Key prefix for event storage
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            **redis_kwargs: Additional Redis connection parameters
        """
        self.host = host
        self.port = port
        self.database = database
        self.password = password
        self.events_prefix = events_prefix
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.redis_kwargs = redis_kwargs
        
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return
        
        self._redis = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.database,
            password=self.password,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            decode_responses=True,
            **self.redis_kwargs
        )
        
        # Test connection
        await self._redis.ping()
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis and self._connected:
            await self._redis.close()
            self._connected = False
    
    def _get_events_key(self) -> str:
        """Get Redis key for events sorted set."""
        return f"{self.events_prefix}:events"
    
    def _get_event_key(self, event_id: str) -> str:
        """Get Redis key for an event."""
        return f"{self.events_prefix}:event:{event_id}"
    
    async def log_event(self, event: TaskEvent) -> None:
        """
        Log a task event.
        
        Args:
            event: The event to log
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        # Store event data
        event_key = self._get_event_key(event.id)
        event_data = msgspec.json.encode(event).decode('utf-8')
        await self._redis.set(event_key, event_data)
        
        # Add to events sorted set with timestamp as score
        events_key = self._get_events_key()
        timestamp_score = event.timestamp.timestamp()
        await self._redis.zadd(events_key, {event.id: timestamp_score})
    
    async def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """
        Get task events.
        
        Args:
            task_id: Filter by task ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of task events
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        events = []
        events_key = self._get_events_key()
        
        # Determine score range for time filtering
        min_score = start_time.timestamp() if start_time else "-inf"
        max_score = end_time.timestamp() if end_time else "+inf"
        
        # Get event IDs in time range
        event_ids = await self._redis.zrangebyscore(
            events_key, min_score, max_score, start=offset, num=limit
        )
        
        # Fetch event data
        for event_id in event_ids:
            event_key = self._get_event_key(event_id)
            event_data = await self._redis.get(event_key)
            
            if event_data:
                try:
                    event = msgspec.json.decode(event_data.encode('utf-8'), type=TaskEvent)
                    
                    # Apply filters
                    if task_id and event.task_id != task_id:
                        continue
                    if event_type and event.event_type != event_type:
                        continue
                    
                    events.append(event)
                except Exception:
                    continue
        
        return events
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """
        Clean up old events.
        
        Args:
            older_than: Delete events older than this timestamp
            
        Returns:
            Number of events cleaned up
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        events_key = self._get_events_key()
        cutoff_score = older_than.timestamp()
        
        # Get old event IDs
        old_event_ids = await self._redis.zrangebyscore(
            events_key, "-inf", cutoff_score
        )
        
        if not old_event_ids:
            return 0
        
        # Delete event data
        event_keys = [self._get_event_key(event_id) for event_id in old_event_ids]
        await self._redis.delete(*event_keys)
        
        # Remove from events sorted set
        await self._redis.zremrangebyscore(events_key, "-inf", cutoff_score)
        
        return len(old_event_ids)


class RedisEventStorage(AsyncRedisEventStorage):
    """
    Synchronous wrapper around AsyncRedisEventStorage.
    
    This class provides a synchronous interface to the async Redis event storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to Redis (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from Redis (sync)."""
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
    
    # Sync context manager support
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()