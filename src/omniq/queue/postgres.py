"""PostgreSQL queue implementations for OmniQ.

This module provides concrete PostgreSQL-based implementations of the queue interface:
- AsyncPostgresQueue and PostgresQueue: Task queue with locking mechanism using asyncpg

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import anyio
import asyncpg
import msgspec

from .base import BaseQueue
from ..models.task import Task


class AsyncPostgresQueue(BaseQueue):
    """Async PostgreSQL-based task queue implementation.
    
    Features:
    - Multiple named queues support using queue_name column
    - Transactional task locking with database row locking
    - Persistent storage with PostgreSQL
    - Connection pooling for efficiency
    """
    
    def __init__(
        self,
        dsn: str,
        table_name: str = "omniq_tasks",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the async PostgreSQL queue.
        
        Args:
            dsn: PostgreSQL connection string
            table_name: Name of the tasks table
            max_connections: Maximum number of connections in the pool
            **connection_kwargs: Additional connection arguments for asyncpg
        """
        self.dsn = dsn
        self.table_name = table_name
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the database connection pool and tables are initialized."""
        if self._initialized:
            return
        
        # Create connection pool
        self.pool = await asyncpg.create_pool(
            self.dsn,
            max_size=self.max_connections,
            **self.connection_kwargs
        )
        
        # Create table if it doesn't exist
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id UUID PRIMARY KEY,
                    queue_name VARCHAR(255) NOT NULL DEFAULT 'default',
                    func_name TEXT NOT NULL,
                    args JSONB NOT NULL,
                    kwargs JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    ttl_seconds INTEGER,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    locked_at TIMESTAMP WITH TIME ZONE,
                    locked_by VARCHAR(255),
                    lock_timeout_seconds INTEGER,
                    priority INTEGER DEFAULT 0,
                    INDEX (queue_name, status, priority, created_at)
                )
            """)
        
        self._initialized = True
    
    async def _acquire_lock(
        self, 
        conn: asyncpg.Connection, 
        task_id: uuid.UUID, 
        lock_timeout: Optional[timedelta] = None,
        worker_id: str = "worker"
    ) -> bool:
        """Acquire a lock for a task using database row locking.
        
        Args:
            conn: Database connection
            task_id: ID of the task to lock
            lock_timeout: How long to hold the lock
            worker_id: Identifier for the worker acquiring the lock
            
        Returns:
            True if lock was acquired, False otherwise
        """
        lock_timeout_seconds = int(lock_timeout.total_seconds()) if lock_timeout else None
        
        # Try to update the task with lock information
        # This uses a WHERE clause to ensure we only lock pending tasks
        result = await conn.execute(
            f"""
            UPDATE {self.table_name}
            SET 
                status = 'processing',
                locked_at = NOW(),
                locked_by = $1,
                lock_timeout_seconds = $2
            WHERE id = $3 AND status = 'pending'
            """,
            worker_id,
            lock_timeout_seconds,
            task_id
        )
        
        # Check if any rows were updated
        return "UPDATE 1" in result
    
    async def _release_lock(self, conn: asyncpg.Connection, task_id: uuid.UUID) -> None:
        """Release a lock for a task.
        
        Args:
            conn: Database connection
            task_id: ID of the task to unlock
        """
        await conn.execute(
            f"""
            UPDATE {self.table_name}
            SET 
                status = 'pending',
                locked_at = NULL,
                locked_by = NULL,
                lock_timeout_seconds = NULL
            WHERE id = $1 AND status = 'processing'
            """,
            task_id
        )
    
    async def _cleanup_expired_locks(self, conn: asyncpg.Connection) -> None:
        """Clean up expired locks.
        
        Args:
            conn: Database connection
        """
        await conn.execute(
            f"""
            UPDATE {self.table_name}
            SET 
                status = 'pending',
                locked_at = NULL,
                locked_by = NULL,
                lock_timeout_seconds = NULL
            WHERE status = 'processing' 
            AND locked_at IS NOT NULL 
            AND lock_timeout_seconds IS NOT NULL
            AND (locked_at + (lock_timeout_seconds || ' seconds')::INTERVAL) < NOW()
            """)
    
    async def enqueue_async(self, task: Task, queue_name: str = "default") -> None:
        """Enqueue a task asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} 
                (id, queue_name, func_name, args, kwargs, created_at, ttl_seconds, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
                """,
                task.id,
                queue_name,
                task.func_name,
                json.dumps(task.args),
                json.dumps(task.kwargs),
                task.created_at,
                int(task.ttl.total_seconds()) if task.ttl else None
            )
    
    async def dequeue_async(self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            # Clean up expired locks first
            await self._cleanup_expired_locks(conn)
            
            # Get the oldest pending task with priority ordering
            row = await conn.fetchrow(
                f"""
                SELECT id, func_name, args, kwargs, created_at, ttl_seconds
                FROM {self.table_name}
                WHERE queue_name = $1 AND status = 'pending'
                ORDER BY priority DESC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,
                queue_name
            )
            
            if not row:
                return None
            
            # Try to acquire lock
            task_id = row['id']
            if await self._acquire_lock(conn, task_id, lock_timeout):
                # Reconstruct the task
                return Task(
                    id=task_id,
                    func_name=row['func_name'],
                    args=tuple(json.loads(row['args'])),
                    kwargs=json.loads(row['kwargs']),
                    created_at=row['created_at'],
                    ttl=timedelta(seconds=row['ttl_seconds']) if row['ttl_seconds'] else None
                )
            
            return None
    
    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = $1",
                task_id
            )
    
    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            await self._release_lock(conn, task_id)
    
    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE queue_name = $1 AND status = 'pending'",
                queue_name
            )
            return result or 0
    
    async def cleanup_expired_tasks_async(self, queue_name: Optional[str] = None) -> int:
        """Clean up expired tasks from the queue.
        
        Args:
            queue_name: Specific queue to clean up, or None for all queues
            
        Returns:
            Number of expired tasks removed
        """
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            if queue_name:
                # Clean up specific queue
                result = await conn.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE queue_name = $1
                    AND ttl_seconds IS NOT NULL
                    AND (created_at + (ttl_seconds || ' seconds')::INTERVAL) < NOW()
                    """,
                    queue_name
                )
            else:
                # Clean up all queues
                result = await conn.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE ttl_seconds IS NOT NULL
                    AND (created_at + (ttl_seconds || ' seconds')::INTERVAL) < NOW()
                    """
                )
            
            # Extract the number of rows deleted from the result
            # PostgreSQL returns "DELETE n" where n is the number of rows
            return int(result.split()[-1])
    
    async def list_queues_async(self) -> List[str]:
        """List all available queue names."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT DISTINCT queue_name FROM {self.table_name} ORDER BY queue_name"
            )
            return [row['queue_name'] for row in rows]
    
    async def close_async(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False


class PostgresQueue(AsyncPostgresQueue):
    """Synchronous wrapper for AsyncPostgresQueue."""
    
    def enqueue(self, task: Task, queue_name: str = "default") -> None:
        """Synchronous wrapper for enqueue_async."""
        anyio.run(self.enqueue_async, task, queue_name)
    
    def dequeue(self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None) -> Optional[Task]:
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