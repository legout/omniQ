"""SQLite queue implementations for OmniQ.

This module provides concrete SQLite-based implementations of the queue interface:
- AsyncSQLiteQueue and SQLiteQueue: Task queue with locking mechanism

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Tuple, Dict
import aiosqlite
import anyio
import logging

from .base import BaseQueue
from ..models.task import Task
from ..serialization.manager import SerializationManager
from ..serialization.base import SerializationError, DeserializationError


class AsyncSQLiteQueue(BaseQueue):
    """Async SQLite-based task queue implementation.

    Features:
    - Multiple named queues support
    - Transactional task locking
    - Automatic schema creation
    - Serialization management for complex task arguments
    """

    def __init__(self, db_path: str):
        """Initialize the async SQLite queue.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
        self._serialization_manager = SerializationManager()
        self._conn: Optional[aiosqlite.Connection] = None
        self._conn_lock = anyio.Lock()

    async def _ensure_initialized(self):
        """Ensure the database schema is initialized."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    func_name TEXT NOT NULL,
                    args_bytes BLOB NOT NULL,
                    kwargs_bytes BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    ttl_seconds INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    locked_at TEXT,
                    lock_timeout_seconds INTEGER
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_queue_status
                ON tasks(queue_name, status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_locked_at
                ON tasks(locked_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_created_at
                ON tasks(created_at)
            """)
            await db.commit()

        self._initialized = True

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection, creating one if necessary."""
        if self._conn is None:
            async with self._conn_lock:
                # Double-check pattern to prevent race condition
                if self._conn is None:
                    self._conn = await aiosqlite.connect(self.db_path)
                    await self._conn.execute("PRAGMA journal_mode=WAL;")
        return self._conn

    async def close(self) -> None:
        """Close the database connection if it's open."""
        if self._conn is not None:
            async with self._conn_lock:
                if self._conn is not None:
                    await self._conn.close()
                    self._conn = None

    async def __aenter__(self):
        """Enter async context manager, ensuring initialization."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager, closing the connection."""
        await self.close()

    async def enqueue_async(
        self,
        task: Optional[Task] = None,
        func: Optional[Callable] = None,
        func_name: Optional[str] = None,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        ttl: Optional[timedelta] = None,
        queue_name: str = "default",
    ) -> None:
        """Enqueue a task asynchronously."""
        await self._ensure_initialized()

        # Create a Task object if one is not provided
        if task is None:
            # Validate that either func or func_name is provided
            if func is None and func_name is None:
                raise ValueError(
                    "Either func or func_name must be provided when task is None"
                )

            # Determine func_name
            if func_name is None:
                func_name = func.__qualname__

            # Default args and kwargs if not provided
            if args is None:
                args = ()
            if kwargs is None:
                kwargs = {}

            # Create the Task instance
            task = Task(
                id=uuid.uuid4(),
                func_name=func_name,
                args=args,
                kwargs=kwargs,
                created_at=datetime.utcnow(),
                ttl=ttl,
            )

        # Serialize task data
        try:
            args_bytes = self._serialization_manager.serialize(task.args)
            kwargs_bytes = self._serialization_manager.serialize(task.kwargs)
        except SerializationError as e:
            logging.error(f"Failed to serialize task data: {e}")
            raise

        ttl_seconds = int(task.ttl.total_seconds()) if task.ttl else None

        db = await self._get_connection()
        await db.execute(
            """
            INSERT INTO tasks (
                id, queue_name, func_name, args_bytes, kwargs_bytes,
                created_at, ttl_seconds, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
            (
                str(task.id),
                queue_name,
                task.func_name,
                args_bytes,
                kwargs_bytes,
                task.created_at.isoformat(),
                ttl_seconds,
            ),
        )
        await db.commit()

    async def dequeue_async(
        self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None
    ) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()

        lock_timeout_seconds = (
            int(lock_timeout.total_seconds()) if lock_timeout else None
        )
        now = datetime.utcnow()

        db = await self._get_connection()
        # Start transaction with immediate lock to prevent race conditions
        await db.execute("BEGIN IMMEDIATE")

        try:
            # First, release any expired locks
            if lock_timeout_seconds:
                expired_time = now - timedelta(seconds=lock_timeout_seconds)
                await db.execute(
                    """
                    UPDATE tasks
                    SET status = 'pending', locked_at = NULL, lock_timeout_seconds = NULL
                    WHERE status = 'processing'
                    AND locked_at < ?
                    AND queue_name = ?
                """,
                    (expired_time.isoformat(), queue_name),
                )

            # Find and lock the next available task in a single operation to prevent race conditions
            cursor = await db.execute(
                """
                UPDATE tasks
                SET status = 'processing', locked_at = ?, lock_timeout_seconds = ?
                WHERE id = (
                    SELECT id FROM tasks
                    WHERE queue_name = ? AND status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING id, func_name, args_bytes, kwargs_bytes, created_at, ttl_seconds
            """,
                (now.isoformat(), lock_timeout_seconds, queue_name),
            )

            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None

            (
                task_id,
                func_name,
                args_bytes,
                kwargs_bytes,
                created_at_str,
                ttl_seconds,
            ) = row

            await db.commit()

            # Reconstruct the task with deserialization
            try:
                args = tuple(self._serialization_manager.deserialize(args_bytes))
                kwargs = self._serialization_manager.deserialize(kwargs_bytes)
            except DeserializationError as e:
                logging.error(
                    f"Failed to deserialize task data for task {task_id}: {e}"
                )
                # Release the task back to the queue since we can't process it
                await self.release_task(uuid.UUID(task_id))
                return None

            created_at = datetime.fromisoformat(created_at_str)
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None

            return Task(
                id=uuid.UUID(task_id),
                func_name=func_name,
                args=args,
                kwargs=kwargs,
                created_at=created_at,
                ttl=ttl,
            )

        except Exception as e:
            await db.rollback()
            logging.error(f"Error during dequeue operation: {e}")
            raise

    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()

        db = await self._get_connection()
        await db.execute("DELETE FROM tasks WHERE id = ?", (str(task_id),))
        await db.commit()

    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()

        db = await self._get_connection()
        await db.execute(
            """
            UPDATE tasks
            SET status = 'pending', locked_at = NULL, lock_timeout_seconds = NULL
            WHERE id = ?
        """,
            (str(task_id),),
        )
        await db.commit()

    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        await self._ensure_initialized()

        db = await self._get_connection()
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE queue_name = ? AND status = 'pending'
        """,
            (queue_name,),
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def cleanup_expired_tasks_async(self) -> int:
        """Clean up expired tasks from all queues asynchronously.

        Returns:
            Number of expired tasks removed
        """
        await self._ensure_initialized()
        now = datetime.utcnow()

        db = await self._get_connection()
        # Clean up all queues
        cursor = await db.execute(
            """
            DELETE FROM tasks
            WHERE ttl_seconds IS NOT NULL
            AND datetime(created_at, '+' || ttl_seconds || ' seconds') < ?
        """,
            (now.isoformat(),),
        )

        await db.commit()
        return cursor.rowcount

    async def list_queues_async(self) -> List[str]:
        """List all available queue names."""
        await self._ensure_initialized()

        db = await self._get_connection()
        cursor = await db.execute("SELECT DISTINCT queue_name FROM tasks")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


class SQLiteQueue(AsyncSQLiteQueue):
    """Synchronous wrapper for AsyncSQLiteQueue."""

    def enqueue(
        self,
        task: Optional[Task] = None,
        func: Optional[Callable] = None,
        func_name: Optional[str] = None,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        ttl: Optional[timedelta] = None,
        queue_name: str = "default",
    ) -> None:
        """Synchronous wrapper for enqueue_async."""
        anyio.run(
            self.enqueue_async, task, func, func_name, args, kwargs, ttl, queue_name
        )

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

    def cleanup_expired_tasks(self) -> int:
        """Synchronous wrapper for cleanup_expired_tasks_async."""
        return anyio.run(self.cleanup_expired_tasks_async)
