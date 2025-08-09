"""SQLite queue implementations for OmniQ.

This module provides concrete SQLite-based implementations of the queue interface:
- AsyncSQLiteQueue and SQLiteQueue: Task queue with locking mechanism

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiosqlite
import anyio
import msgspec

from .base import BaseQueue
from ..models.task import Task


class AsyncSQLiteQueue(BaseQueue):
    """Async SQLite-based task queue implementation.
    
    Features:
    - Multiple named queues support
    - Transactional task locking
    - Automatic schema creation
    """
    
    def __init__(self, db_path: str):
        """Initialize the async SQLite queue.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
    
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
                    args_json TEXT NOT NULL,
                    kwargs_json TEXT NOT NULL,
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
            await db.commit()
        
        self._initialized = True
    
    async def enqueue_async(self, task: Task, queue_name: str = "default") -> None:
        """Enqueue a task asynchronously."""
        await self._ensure_initialized()
        
        # Serialize task data
        args_json = json.dumps(task.args, default=str)
        kwargs_json = json.dumps(task.kwargs, default=str)
        ttl_seconds = int(task.ttl.total_seconds()) if task.ttl else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO tasks (
                    id, queue_name, func_name, args_json, kwargs_json, 
                    created_at, ttl_seconds, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                str(task.id), queue_name, task.func_name, args_json, kwargs_json,
                task.created_at.isoformat(), ttl_seconds
            ))
            await db.commit()
    
    async def dequeue_async(self, queue_name: str = "default", lock_timeout: Optional[timedelta] = None) -> Optional[Task]:
        """Dequeue and lock a task asynchronously."""
        await self._ensure_initialized()
        
        lock_timeout_seconds = int(lock_timeout.total_seconds()) if lock_timeout else None
        now = datetime.utcnow()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Start transaction
            await db.execute("BEGIN IMMEDIATE")
            
            try:
                # First, release any expired locks
                if lock_timeout_seconds:
                    expired_time = now - timedelta(seconds=lock_timeout_seconds)
                    await db.execute("""
                        UPDATE tasks 
                        SET status = 'pending', locked_at = NULL, lock_timeout_seconds = NULL
                        WHERE status = 'processing' 
                        AND locked_at < ?
                        AND queue_name = ?
                    """, (expired_time.isoformat(), queue_name))
                
                # Find and lock the next available task
                cursor = await db.execute("""
                    SELECT id, func_name, args_json, kwargs_json, created_at, ttl_seconds
                    FROM tasks 
                    WHERE queue_name = ? AND status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                """, (queue_name,))
                
                row = await cursor.fetchone()
                if not row:
                    await db.rollback()
                    return None
                
                task_id, func_name, args_json, kwargs_json, created_at_str, ttl_seconds = row
                
                # Lock the task
                await db.execute("""
                    UPDATE tasks 
                    SET status = 'processing', locked_at = ?, lock_timeout_seconds = ?
                    WHERE id = ?
                """, (now.isoformat(), lock_timeout_seconds, task_id))
                
                await db.commit()
                
                # Reconstruct the task
                args = tuple(json.loads(args_json))
                kwargs = json.loads(kwargs_json)
                created_at = datetime.fromisoformat(created_at_str)
                ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None
                
                return Task(
                    id=uuid.UUID(task_id),
                    func_name=func_name,
                    args=args,
                    kwargs=kwargs,
                    created_at=created_at,
                    ttl=ttl
                )
                
            except Exception:
                await db.rollback()
                raise
    
    async def complete_task_async(self, task_id: uuid.UUID) -> None:
        """Mark a task as completed and remove it from the queue."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (str(task_id),))
            await db.commit()
    
    async def release_task_async(self, task_id: uuid.UUID) -> None:
        """Release a locked task back to the queue."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE tasks
                SET status = 'pending', locked_at = NULL, lock_timeout_seconds = NULL
                WHERE id = ?
            """, (str(task_id),))
            await db.commit()
    
    async def get_queue_size_async(self, queue_name: str = "default") -> int:
        """Get the number of pending tasks in a queue."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE queue_name = ? AND status = 'pending'
            """, (queue_name,))
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def cleanup_expired_tasks_async(self, queue_name: Optional[str] = None) -> int:
        """Clean up expired tasks from the queue.
        
        Args:
            queue_name: Specific queue to clean up, or None for all queues
            
        Returns:
            Number of expired tasks removed
        """
        await self._ensure_initialized()
        now = datetime.utcnow()
        
        async with aiosqlite.connect(self.db_path) as db:
            if queue_name:
                # Clean up specific queue
                cursor = await db.execute("""
                    DELETE FROM tasks
                    WHERE queue_name = ?
                    AND ttl_seconds IS NOT NULL
                    AND datetime(created_at, '+' || ttl_seconds || ' seconds') < ?
                """, (queue_name, now.isoformat()))
            else:
                # Clean up all queues
                cursor = await db.execute("""
                    DELETE FROM tasks
                    WHERE ttl_seconds IS NOT NULL
                    AND datetime(created_at, '+' || ttl_seconds || ' seconds') < ?
                """, (now.isoformat(),))
            
            await db.commit()
            return cursor.rowcount
    
    async def list_queues_async(self) -> List[str]:
        """List all available queue names."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT queue_name FROM tasks")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


class SQLiteQueue(AsyncSQLiteQueue):
    """Synchronous wrapper for AsyncSQLiteQueue."""
    
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
    
    def cleanup_expired_tasks(self, queue_name: Optional[str] = None) -> int:
        """Synchronous wrapper for cleanup_expired_tasks_async."""
        return anyio.run(self.cleanup_expired_tasks_async, queue_name)