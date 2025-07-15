"""
NATS storage implementations for OmniQ.

This module provides NATS-based storage implementations for task queues,
result storage, event storage, and schedule storage using NATS JetStream
for persistent messaging and distributed task processing.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import nats
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext
import msgspec

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent
from ..models.schedule import Schedule


class AsyncNATSQueue(BaseTaskQueue):
    """
    Async NATS-based task queue implementation using JetStream.
    
    This class implements the BaseTaskQueue interface using NATS JetStream
    for persistent task storage with support for multiple queues,
    priority ordering, and distributed processing.
    """
    
    def __init__(
        self,
        servers: Optional[List[str]] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        tasks_subject: str = "omniq.tasks",
        connect_timeout: float = 2.0,
        reconnect_time_wait: float = 2.0,
        max_reconnect_attempts: int = 60,
        queue_group: str = "omniq_workers",
        **nats_kwargs
    ):
        """
        Initialize NATS task queue.
        
        Args:
            servers: List of NATS server URLs
            user: NATS username
            password: NATS password
            token: NATS token
            tls: Enable TLS
            tls_cert: TLS certificate file path
            tls_key: TLS key file path
            tls_ca: TLS CA file path
            tasks_subject: Subject prefix for task storage
            connect_timeout: Connection timeout in seconds
            reconnect_time_wait: Reconnect wait time in seconds
            max_reconnect_attempts: Maximum reconnect attempts
            queue_group: Queue group name for load balancing
            **nats_kwargs: Additional NATS connection parameters
        """
        self.servers = servers or ["nats://localhost:4222"]
        self.user = user
        self.password = password
        self.token = token
        self.tls = tls
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.tls_ca = tls_ca
        self.tasks_subject = tasks_subject
        self.connect_timeout = connect_timeout
        self.reconnect_time_wait = reconnect_time_wait
        self.max_reconnect_attempts = max_reconnect_attempts
        self.queue_group = queue_group
        self.nats_kwargs = nats_kwargs
        
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._connected = False
        self._stream_name = "OMNIQ_TASKS"
    
    async def connect(self) -> None:
        """Connect to NATS and set up JetStream."""
        if self._connected:
            return
        
        # Prepare connection options
        options = {
            "servers": self.servers,
            "connect_timeout": self.connect_timeout,
            "reconnect_time_wait": self.reconnect_time_wait,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            **self.nats_kwargs
        }
        
        # Add authentication
        if self.user and self.password:
            options["user"] = self.user
            options["password"] = self.password
        elif self.token:
            options["token"] = self.token
        
        # Add TLS configuration
        if self.tls:
            options["tls"] = True
            if self.tls_cert:
                options["tls_cert"] = self.tls_cert
            if self.tls_key:
                options["tls_key"] = self.tls_key
            if self.tls_ca:
                options["tls_ca"] = self.tls_ca
        
        # Connect to NATS
        self._nc = await nats.connect(**options)
        
        # Get JetStream context
        self._js = self._nc.jetstream()
        
        # Create or update stream
        await self._ensure_stream()
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._connected:
            await self._nc.close()
            self._connected = False
    
    async def _ensure_stream(self) -> None:
        """Ensure the tasks stream exists."""
        if not self._js:
            raise RuntimeError("JetStream not initialized")
        
        try:
            # Try to get existing stream info
            await self._js.stream_info(self._stream_name)
        except Exception:
            # Stream doesn't exist, create it
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType
            
            config = StreamConfig(
                name=self._stream_name,
                subjects=[f"{self.tasks_subject}.>"],
                retention=RetentionPolicy.WORK_QUEUE,
                storage=StorageType.FILE,
                max_age=timedelta(days=7).total_seconds(),  # 7 days retention
                max_msgs=1000000,  # 1M messages max
                discard_new_per_subject=False,
            )
            
            await self._js.add_stream(config)
    
    def _get_task_subject(self, queue_name: str, task_id: str) -> str:
        """Get NATS subject for a task."""
        return f"{self.tasks_subject}.{queue_name}.{task_id}"
    
    def _get_queue_subject(self, queue_name: str) -> str:
        """Get NATS subject for a queue."""
        return f"{self.tasks_subject}.{queue_name}.>"
    
    async def enqueue(self, task: Task) -> str:
        """
        Enqueue a task for processing.
        
        Args:
            task: The task to enqueue
            
        Returns:
            The task ID
        """
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        # Serialize task
        task_data = msgspec.json.encode(task)
        
        # Publish to JetStream with priority in headers
        subject = self._get_task_subject(task.queue_name, task.id)
        headers = {
            "priority": str(task.priority),
            "queue": task.queue_name,
            "task_id": task.id,
            "created_at": task.created_at.isoformat(),
        }
        
        if task.run_at:
            headers["run_at"] = task.run_at.isoformat()
        
        await self._js.publish(subject, task_data, headers=headers)
        
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
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        # Simple implementation using basic NATS subscription
        # In production, you'd want to use JetStream consumers properly
        start_time = datetime.utcnow()
        
        while True:
            # Try each queue in priority order
            for queue_name in queues:
                subject = self._get_queue_subject(queue_name)
                
                try:
                    # Subscribe to queue subject
                    if not self._nc:
                        continue
                    sub = await self._nc.subscribe(subject)
                    
                    try:
                        # Try to get a message with short timeout
                        msg = await sub.next_msg(timeout=0.1)
                        
                        # Deserialize task
                        task_data = msg.data
                        task = msgspec.json.decode(task_data, type=Task)
                        
                        # Check if task is ready to run
                        if task.is_ready_to_run():
                            # Update task status
                            task.status = TaskStatus.RUNNING
                            await sub.unsubscribe()
                            return task
                        else:
                            # Task not ready, continue
                            await sub.unsubscribe()
                            continue
                            
                    except Exception:
                        # No message available in this queue
                        await sub.unsubscribe()
                        continue
                        
                except Exception:
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
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        # NATS JetStream doesn't support direct key-value lookup
        # We need to search through messages
        # This is a limitation of the current implementation
        # In a production system, you might want to use NATS KV store
        # or maintain a separate index
        
        # For now, we'll return None and rely on the task being
        # available through dequeue operations
        return None
    
    async def update_task(self, task: Task) -> None:
        """
        Update a task in the queue.
        
        Args:
            task: The updated task
        """
        # NATS JetStream is append-only, so we can't update existing messages
        # We would need to publish a new message with updated data
        # This is a design limitation that would need to be addressed
        # in a production implementation, possibly using NATS KV store
        pass
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the queue.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if task was deleted, False if not found
        """
        # NATS JetStream doesn't support direct message deletion by ID
        # Messages are consumed and acknowledged, which removes them
        # This operation is not directly supported
        return False
    
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
        # NATS JetStream doesn't support listing messages directly
        # This would require a separate indexing mechanism
        return []
    
    async def get_queue_size(self, queue_name: str) -> int:
        """
        Get the number of tasks in a queue.
        
        Args:
            queue_name: The queue name
            
        Returns:
            Number of tasks in the queue
        """
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        try:
            # Get stream info to check message count
            info = await self._js.stream_info(self._stream_name)
            # This returns total messages in stream, not per queue
            # Would need consumer-specific stats for accurate count
            return info.state.messages
        except Exception:
            return 0
    
    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks.
        
        Returns:
            Number of tasks cleaned up
        """
        # NATS JetStream handles message expiration automatically
        # based on stream configuration (max_age)
        return 0


class NATSQueue(AsyncNATSQueue):
    """
    Synchronous wrapper around AsyncNATSQueue.
    
    This class provides a synchronous interface to the async NATS queue
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to NATS (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from NATS (sync)."""
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


class AsyncNATSResultStorage(BaseResultStorage):
    """
    Async NATS-based result storage implementation using JetStream.
    
    This class implements the BaseResultStorage interface using NATS JetStream
    for persistent result storage with TTL support.
    """
    
    def __init__(
        self,
        servers: Optional[List[str]] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        results_subject: str = "omniq.results",
        connect_timeout: float = 2.0,
        reconnect_time_wait: float = 2.0,
        max_reconnect_attempts: int = 60,
        **nats_kwargs
    ):
        """
        Initialize NATS result storage.
        
        Args:
            servers: List of NATS server URLs
            user: NATS username
            password: NATS password
            token: NATS token
            tls: Enable TLS
            tls_cert: TLS certificate file path
            tls_key: TLS key file path
            tls_ca: TLS CA file path
            results_subject: Subject prefix for result storage
            connect_timeout: Connection timeout in seconds
            reconnect_time_wait: Reconnect wait time in seconds
            max_reconnect_attempts: Maximum reconnect attempts
            **nats_kwargs: Additional NATS connection parameters
        """
        self.servers = servers or ["nats://localhost:4222"]
        self.user = user
        self.password = password
        self.token = token
        self.tls = tls
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.tls_ca = tls_ca
        self.results_subject = results_subject
        self.connect_timeout = connect_timeout
        self.reconnect_time_wait = reconnect_time_wait
        self.max_reconnect_attempts = max_reconnect_attempts
        self.nats_kwargs = nats_kwargs
        
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._kv = None  # Key-Value store for results
        self._connected = False
        self._bucket_name = "omniq_results"
    
    async def connect(self) -> None:
        """Connect to NATS and set up Key-Value store."""
        if self._connected:
            return
        
        # Prepare connection options
        options = {
            "servers": self.servers,
            "connect_timeout": self.connect_timeout,
            "reconnect_time_wait": self.reconnect_time_wait,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            **self.nats_kwargs
        }
        
        # Add authentication
        if self.user and self.password:
            options["user"] = self.user
            options["password"] = self.password
        elif self.token:
            options["token"] = self.token
        
        # Add TLS configuration
        if self.tls:
            options["tls"] = True
            if self.tls_cert:
                options["tls_cert"] = self.tls_cert
            if self.tls_key:
                options["tls_key"] = self.tls_key
            if self.tls_ca:
                options["tls_ca"] = self.tls_ca
        
        # Connect to NATS
        self._nc = await nats.connect(**options)
        
        # Get JetStream context
        self._js = self._nc.jetstream()
        
        # Create or get Key-Value bucket for results
        await self._ensure_kv_bucket()
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._connected:
            await self._nc.close()
            self._connected = False
    
    async def _ensure_kv_bucket(self) -> None:
        """Ensure the results KV bucket exists."""
        if not self._js:
            raise RuntimeError("JetStream not initialized")
        
        try:
            # Try to get existing bucket
            self._kv = await self._js.key_value(self._bucket_name)
        except Exception:
            # Bucket doesn't exist, create it
            self._kv = await self._js.create_key_value(
                bucket=self._bucket_name,
                ttl=timedelta(days=7).total_seconds(),  # 7 days TTL
                max_value_size=1024 * 1024,  # 1MB max value size
            )
    
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """
        Get a task result by task ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task result or None if not found
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        try:
            entry = await self._kv.get(task_id)
            if entry and entry.value:
                return msgspec.json.decode(entry.value, type=TaskResult)
        except Exception:
            pass
        
        return None
    
    async def set(self, result: TaskResult) -> None:
        """
        Store a task result.
        
        Args:
            result: The task result to store
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        result_data = msgspec.json.encode(result)
        await self._kv.put(result.task_id, result_data)
    
    async def delete(self, task_id: str) -> bool:
        """
        Delete a task result.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if result was deleted, False if not found
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        try:
            await self._kv.delete(task_id)
            return True
        except Exception:
            return False
    
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
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        results = []
        
        try:
            # Get all keys
            keys = await self._kv.keys()
            
            # Process keys with offset and limit
            for i, key in enumerate(keys):
                if i < offset:
                    continue
                if limit and len(results) >= limit:
                    break
                
                try:
                    entry = await self._kv.get(key)
                    if entry and entry.value:
                        result = msgspec.json.decode(entry.value, type=TaskResult)
                        if not status or result.status == status:
                            results.append(result)
                except Exception:
                    continue
        except Exception:
            pass
        
        return results
    
    async def cleanup_expired_results(self) -> int:
        """
        Clean up expired results.
        
        Returns:
            Number of results cleaned up
        """
        # NATS KV handles expiration automatically based on TTL
        return 0


class NATSResultStorage(AsyncNATSResultStorage):
    """
    Synchronous wrapper around AsyncNATSResultStorage.
    
    This class provides a synchronous interface to the async NATS result storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to NATS (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from NATS (sync)."""
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


class AsyncNATSEventStorage(BaseEventStorage):
    """
    Async NATS-based event storage implementation using JetStream.
    
    This class implements the BaseEventStorage interface using NATS JetStream
    for persistent event logging with time-based cleanup.
    """
    
    def __init__(
        self,
        servers: Optional[List[str]] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        events_subject: str = "omniq.events",
        connect_timeout: float = 2.0,
        reconnect_time_wait: float = 2.0,
        max_reconnect_attempts: int = 60,
        **nats_kwargs
    ):
        """
        Initialize NATS event storage.
        
        Args:
            servers: List of NATS server URLs
            user: NATS username
            password: NATS password
            token: NATS token
            tls: Enable TLS
            tls_cert: TLS certificate file path
            tls_key: TLS key file path
            tls_ca: TLS CA file path
            events_subject: Subject prefix for event storage
            connect_timeout: Connection timeout in seconds
            reconnect_time_wait: Reconnect wait time in seconds
            max_reconnect_attempts: Maximum reconnect attempts
            **nats_kwargs: Additional NATS connection parameters
        """
        self.servers = servers or ["nats://localhost:4222"]
        self.user = user
        self.password = password
        self.token = token
        self.tls = tls
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.tls_ca = tls_ca
        self.events_subject = events_subject
        self.connect_timeout = connect_timeout
        self.reconnect_time_wait = reconnect_time_wait
        self.max_reconnect_attempts = max_reconnect_attempts
        self.nats_kwargs = nats_kwargs
        
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._connected = False
        self._stream_name = "OMNIQ_EVENTS"
    
    async def connect(self) -> None:
        """Connect to NATS and set up JetStream."""
        if self._connected:
            return
        
        # Prepare connection options
        options = {
            "servers": self.servers,
            "connect_timeout": self.connect_timeout,
            "reconnect_time_wait": self.reconnect_time_wait,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            **self.nats_kwargs
        }
        
        # Add authentication
        if self.user and self.password:
            options["user"] = self.user
            options["password"] = self.password
        elif self.token:
            options["token"] = self.token
        
        # Add TLS configuration
        if self.tls:
            options["tls"] = True
            if self.tls_cert:
                options["tls_cert"] = self.tls_cert
            if self.tls_key:
                options["tls_key"] = self.tls_key
            if self.tls_ca:
                options["tls_ca"] = self.tls_ca
        
        # Connect to NATS
        self._nc = await nats.connect(**options)
        
        # Get JetStream context
        self._js = self._nc.jetstream()
        
        # Create or update stream
        await self._ensure_stream()
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._connected:
            await self._nc.close()
            self._connected = False
    
    async def _ensure_stream(self) -> None:
        """Ensure the events stream exists."""
        if not self._js:
            raise RuntimeError("JetStream not initialized")
        
        try:
            # Try to get existing stream info
            await self._js.stream_info(self._stream_name)
        except Exception:
            # Stream doesn't exist, create it
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType
            
            config = StreamConfig(
                name=self._stream_name,
                subjects=[f"{self.events_subject}.>"],
                retention=RetentionPolicy.LIMITS,
                storage=StorageType.FILE,
                max_age=timedelta(days=30).total_seconds(),  # 30 days retention
                max_msgs=10000000,  # 10M messages max
                discard_new_per_subject=False,
            )
            
            await self._js.add_stream(config)
    
    def _get_event_subject(self, event: TaskEvent) -> str:
        """Get NATS subject for an event."""
        return f"{self.events_subject}.{event.event_type}.{event.task_id}"
    
    async def log_event(self, event: TaskEvent) -> None:
        """
        Log a task event.
        
        Args:
            event: The event to log
        """
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        # Serialize event
        event_data = msgspec.json.encode(event)
        
        # Publish to JetStream
        subject = self._get_event_subject(event)
        headers = {
            "event_type": event.event_type,
            "task_id": event.task_id,
            "timestamp": event.timestamp.isoformat(),
        }
        
        await self._js.publish(subject, event_data, headers=headers)
    
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
        if not self._js:
            raise RuntimeError("NATS JetStream not connected")
        
        # NATS JetStream doesn't support complex querying
        # This would require a more sophisticated implementation
        # For now, return empty list
        return []
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """
        Clean up events older than the specified time.
        
        Args:
            older_than: Delete events older than this time
            
        Returns:
            Number of events cleaned up
        """
        # NATS JetStream handles message expiration automatically
        # based on stream configuration (max_age)
        return 0


class NATSEventStorage(AsyncNATSEventStorage):
    """
    Synchronous wrapper around AsyncNATSEventStorage.
    
    This class provides a synchronous interface to the async NATS event storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to NATS (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from NATS (sync)."""
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


class AsyncNATSScheduleStorage(BaseScheduleStorage):
    """
    Async NATS-based schedule storage implementation using JetStream.
    
    This class implements the BaseScheduleStorage interface using NATS JetStream
    for persistent schedule storage with time-based scheduling support.
    """
    
    def __init__(
        self,
        servers: Optional[List[str]] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        schedules_subject: str = "omniq.schedules",
        connect_timeout: float = 2.0,
        reconnect_time_wait: float = 2.0,
        max_reconnect_attempts: int = 60,
        **nats_kwargs
    ):
        """
        Initialize NATS schedule storage.
        
        Args:
            servers: List of NATS server URLs
            user: NATS username
            password: NATS password
            token: NATS token
            tls: Enable TLS
            tls_cert: TLS certificate file path
            tls_key: TLS key file path
            tls_ca: TLS CA file path
            schedules_subject: Subject prefix for schedule storage
            connect_timeout: Connection timeout in seconds
            reconnect_time_wait: Reconnect wait time in seconds
            max_reconnect_attempts: Maximum reconnect attempts
            **nats_kwargs: Additional NATS connection parameters
        """
        self.servers = servers or ["nats://localhost:4222"]
        self.user = user
        self.password = password
        self.token = token
        self.tls = tls
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.tls_ca = tls_ca
        self.schedules_subject = schedules_subject
        self.connect_timeout = connect_timeout
        self.reconnect_time_wait = reconnect_time_wait
        self.max_reconnect_attempts = max_reconnect_attempts
        self.nats_kwargs = nats_kwargs
        
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._kv = None  # Key-Value store for schedules
        self._connected = False
        self._bucket_name = "omniq_schedules"
    
    async def connect(self) -> None:
        """Connect to NATS and set up Key-Value store."""
        if self._connected:
            return
        
        # Prepare connection options
        options = {
            "servers": self.servers,
            "connect_timeout": self.connect_timeout,
            "reconnect_time_wait": self.reconnect_time_wait,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            **self.nats_kwargs
        }
        
        # Add authentication
        if self.user and self.password:
            options["user"] = self.user
            options["password"] = self.password
        elif self.token:
            options["token"] = self.token
        
        # Add TLS configuration
        if self.tls:
            options["tls"] = True
            if self.tls_cert:
                options["tls_cert"] = self.tls_cert
            if self.tls_key:
                options["tls_key"] = self.tls_key
            if self.tls_ca:
                options["tls_ca"] = self.tls_ca
        
        # Connect to NATS
        self._nc = await nats.connect(**options)
        
        # Get JetStream context
        self._js = self._nc.jetstream()
        
        # Create or get Key-Value bucket for schedules
        await self._ensure_kv_bucket()
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._connected:
            await self._nc.close()
            self._connected = False
    
    async def _ensure_kv_bucket(self) -> None:
        """Ensure the schedules KV bucket exists."""
        if not self._js:
            raise RuntimeError("JetStream not initialized")
        
        try:
            # Try to get existing bucket
            self._kv = await self._js.key_value(self._bucket_name)
        except Exception:
            # Bucket doesn't exist, create it
            self._kv = await self._js.create_key_value(
                bucket=self._bucket_name,
                ttl=0,  # No TTL for schedules
                max_value_size=1024 * 1024,  # 1MB max value size
            )
    
    async def create_schedule(self, schedule: Schedule) -> str:
        """
        Create a new schedule.
        
        Args:
            schedule: The schedule to create
            
        Returns:
            The schedule ID
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        schedule_data = msgspec.json.encode(schedule)
        await self._kv.put(schedule.id, schedule_data)
        return schedule.id
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get a schedule by ID.
        
        Args:
            schedule_id: The schedule ID
            
        Returns:
            The schedule or None if not found
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        try:
            entry = await self._kv.get(schedule_id)
            if entry and entry.value:
                return msgspec.json.decode(entry.value, type=Schedule)
        except Exception:
            pass
        
        return None
    
    async def update_schedule(self, schedule: Schedule) -> None:
        """
        Update a schedule.
        
        Args:
            schedule: The updated schedule
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        schedule_data = msgspec.json.encode(schedule)
        await self._kv.put(schedule.id, schedule_data)
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            schedule_id: The schedule ID
            
        Returns:
            True if schedule was deleted, False if not found
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        try:
            await self._kv.delete(schedule_id)
            return True
        except Exception:
            return False
    
    async def save_schedule(self, schedule: Schedule) -> None:
        """
        Save a schedule.
        
        Args:
            schedule: The schedule to save
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        schedule_data = msgspec.json.encode(schedule)
        await self._kv.put(schedule.id, schedule_data)
    
    async def list_schedules(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """
        List schedules.
        
        Args:
            status: Filter by schedule status
            limit: Maximum number of schedules to return
            offset: Number of schedules to skip
            
        Returns:
            List of schedules
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        schedules = []
        
        try:
            # Get all keys
            keys = await self._kv.keys()
            
            # Process keys with offset and limit
            for i, key in enumerate(keys):
                if i < offset:
                    continue
                if limit and len(schedules) >= limit:
                    break
                
                try:
                    entry = await self._kv.get(key)
                    if entry and entry.value:
                        schedule = msgspec.json.decode(entry.value, type=Schedule)
                        if not status or schedule.status == status:
                            schedules.append(schedule)
                except Exception:
                    continue
        except Exception:
            pass
        
        return schedules
    
    async def get_ready_schedules(self) -> List[Schedule]:
        """
        Get schedules that are ready to run.
        
        Returns:
            List of schedules ready to run
        """
        if not self._kv:
            raise RuntimeError("NATS Key-Value store not connected")
        
        ready_schedules = []
        
        try:
            # Get all keys
            keys = await self._kv.keys()
            
            for key in keys:
                try:
                    entry = await self._kv.get(key)
                    if entry and entry.value:
                        schedule = msgspec.json.decode(entry.value, type=Schedule)
                        if schedule.is_ready_to_run():
                            ready_schedules.append(schedule)
                except Exception:
                    continue
        except Exception:
            pass
        
        return ready_schedules


class NATSScheduleStorage(AsyncNATSScheduleStorage):
    """
    Synchronous wrapper around AsyncNATSScheduleStorage.
    
    This class provides a synchronous interface to the async NATS schedule storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to NATS (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from NATS (sync)."""
        asyncio.run(self.disconnect())
    
    def create_schedule_sync(self, schedule: Schedule) -> str:
        """Create a new schedule (sync)."""
        return asyncio.run(self.create_schedule(schedule))
    
    def get_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID (sync)."""
        return asyncio.run(self.get_schedule(schedule_id))
    
    def update_schedule_sync(self, schedule: Schedule) -> None:
        """Update a schedule (sync)."""
        asyncio.run(self.update_schedule(schedule))
    
    def delete_schedule_sync(self, schedule_id: str) -> bool:
        """Delete a schedule (sync)."""
        return asyncio.run(self.delete_schedule(schedule_id))
    
    def save_schedule_sync(self, schedule: Schedule) -> None:
        """Save a schedule (sync)."""
        asyncio.run(self.save_schedule(schedule))
    
    def list_schedules_sync(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules (sync)."""
        return asyncio.run(self.list_schedules(status, limit, offset))
    
    def get_ready_schedules_sync(self) -> List[Schedule]:
        """Get ready schedules (sync)."""
        return asyncio.run(self.get_ready_schedules())
    
    # Sync context manager support
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class NATSBackend:
    """
    Unified NATS backend that combines all NATS storage components.
    
    This class provides a single interface to all NATS-based storage
    implementations, making it easy to configure and use NATS as the
    complete backend for OmniQ.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize NATS backend with configuration.
        
        Args:
            config: NATS configuration dictionary
        """
        self.config = config
        
        # Extract common connection parameters
        connection_params = {
            "servers": config.get("servers", ["nats://localhost:4222"]),
            "user": config.get("user"),
            "password": config.get("password"),
            "token": config.get("token"),
            "tls": config.get("tls", False),
            "tls_cert": config.get("tls_cert"),
            "tls_key": config.get("tls_key"),
            "tls_ca": config.get("tls_ca"),
            "connect_timeout": config.get("connect_timeout", 2.0),
            "reconnect_time_wait": config.get("reconnect_time_wait", 2.0),
            "max_reconnect_attempts": config.get("max_reconnect_attempts", 60),
        }
        
        # Initialize storage components
        self.task_queue = AsyncNATSQueue(
            **connection_params,
            tasks_subject=config.get("tasks_subject", "omniq.tasks"),
            queue_group=config.get("queue_group", "omniq_workers"),
        )
        
        self.result_storage = AsyncNATSResultStorage(
            **connection_params,
            results_subject=config.get("results_subject", "omniq.results"),
        )
        
        self.event_storage = AsyncNATSEventStorage(
            **connection_params,
            events_subject=config.get("events_subject", "omniq.events"),
        )
        
        self.schedule_storage = AsyncNATSScheduleStorage(
            **connection_params,
            schedules_subject=config.get("schedules_subject", "omniq.schedules"),
        )
        
        # Sync wrappers
        self.sync_task_queue = NATSQueue(
            **connection_params,
            tasks_subject=config.get("tasks_subject", "omniq.tasks"),
            queue_group=config.get("queue_group", "omniq_workers"),
        )
        
        self.sync_result_storage = NATSResultStorage(
            **connection_params,
            results_subject=config.get("results_subject", "omniq.results"),
        )
        
        self.sync_event_storage = NATSEventStorage(
            **connection_params,
            events_subject=config.get("events_subject", "omniq.events"),
        )
        
        self.sync_schedule_storage = NATSScheduleStorage(
            **connection_params,
            schedules_subject=config.get("schedules_subject", "omniq.schedules"),
        )
    
    async def connect(self) -> None:
        """Connect all storage components."""
        await asyncio.gather(
            self.task_queue.connect(),
            self.result_storage.connect(),
            self.event_storage.connect(),
            self.schedule_storage.connect(),
        )
    
    async def disconnect(self) -> None:
        """Disconnect all storage components."""
        await asyncio.gather(
            self.task_queue.disconnect(),
            self.result_storage.disconnect(),
            self.event_storage.disconnect(),
            self.schedule_storage.disconnect(),
        )
    
    def connect_sync(self) -> None:
        """Connect all storage components (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect all storage components (sync)."""
        asyncio.run(self.disconnect())
    
    @asynccontextmanager
    async def async_context(self):
        """Async context manager for the backend."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


# Factory function for creating NATS backend from config
def create_nats_backend(config: Dict[str, Any]) -> NATSBackend:
    """
    Create a NATS backend from configuration.
    
    Args:
        config: NATS configuration dictionary
        
    Returns:
        Configured NATS backend instance
    """
    return NATSBackend(config)