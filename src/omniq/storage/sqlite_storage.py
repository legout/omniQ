"""SQLite storage backend for tasks and results in OmniQ."""

import sqlite3
import aiosqlite
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import threading
import asyncio
from contextlib import contextmanager, asynccontextmanager

from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.storage.base import BaseTaskStorage, BaseResultStorage
from omniq.serialization.manager import SerializationManager


class SQLiteStorage(BaseTaskStorage, BaseResultStorage):
    """SQLite storage backend for tasks and results with sync and async methods."""
    
    def __init__(self, db_path: str, serializer: Optional[SerializationManager] = None):
        """
        Initialize the SQLite storage backend.
        
        Args:
            db_path (str): Path to the SQLite database file.
            serializer (Optional[SerializationManager]): Serialization manager for tasks and results.
        """
        self.db_path = db_path
        self.serializer = serializer or SerializationManager()
        self._init_db()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
    def _init_db(self) -> None:
        """Initialize the database schema with tables for tasks, results, and schedules."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    serialized_data BLOB NOT NULL,
                    serialization_format TEXT NOT NULL,
                    ttl_timestamp REAL,
                    created_at REAL NOT NULL
                )
            ''')
            # Results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    serialized_data BLOB NOT NULL,
                    serialization_format TEXT NOT NULL,
                    ttl_timestamp REAL,
                    created_at REAL NOT NULL
                )
            ''')
            # Schedules table for state management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    active INTEGER NOT NULL
                )
            ''')
            # Indexes for efficient querying and cleanup
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_ttl ON tasks(ttl_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_ttl ON results(ttl_timestamp)')
            conn.commit()
    
    @contextmanager
    def _get_sync_connection(self):
        """Context manager for synchronous database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    @asynccontextmanager
    async def _get_async_connection(self):
        """Async context manager for asynchronous database connections."""
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()
    
    def store_task(self, task: Task) -> None:
        """Synchronously store a task in the backend."""
        serialized = self.serializer.serialize(task)
        ttl_timestamp = None
        if task.ttl is not None:
            ttl_timestamp = (task.created_at.timestamp() + task.ttl) if task.created_at else datetime.now().timestamp() + task.ttl
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO tasks (task_id, serialized_data, serialization_format, ttl_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task.id, serialized['data'], serialized['__serialization_format__'].decode('utf-8'), 
                      ttl_timestamp, task.created_at.timestamp() if task.created_at else datetime.now().timestamp()))
                conn.commit()
    
    async def store_task_async(self, task: Task) -> None:
        """Asynchronously store a task in the backend."""
        serialized = self.serializer.serialize(task)
        ttl_timestamp = None
        if task.ttl is not None:
            ttl_timestamp = (task.created_at.timestamp() + task.ttl) if task.created_at else datetime.now().timestamp() + task.ttl
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                await conn.execute('''
                    INSERT OR REPLACE INTO tasks (task_id, serialized_data, serialization_format, ttl_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task.id, serialized['data'], serialized['__serialization_format__'].decode('utf-8'), 
                      ttl_timestamp, task.created_at.timestamp() if task.created_at else datetime.now().timestamp()))
                await conn.commit()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Synchronously retrieve a task by ID."""
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM tasks WHERE task_id = ?', (task_id,))
            result = cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, Task)
            return None
    
    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Asynchronously retrieve a task by ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM tasks WHERE task_id = ?', (task_id,))
            result = await cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, Task)
            return None
    
    def get_tasks(self, limit: int = 100) -> List[Task]:
        """Synchronously retrieve a list of tasks, optionally limited."""
        tasks = []
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM tasks ORDER BY created_at DESC LIMIT ?', (limit,))
            for row in cursor.fetchall():
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                tasks.append(self.serializer.deserialize(serialized_data, Task))
        return tasks
    
    async def get_tasks_async(self, limit: int = 100) -> List[Task]:
        """Asynchronously retrieve a list of tasks, optionally limited."""
        tasks = []
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM tasks ORDER BY created_at DESC LIMIT ?', (limit,))
            rows = await cursor.fetchall()
            for row in rows:
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                tasks.append(self.serializer.deserialize(serialized_data, Task))
        return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """Synchronously delete a task by ID."""
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    async def delete_task_async(self, task_id: str) -> bool:
        """Asynchronously delete a task by ID."""
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
                await conn.commit()
                return cursor.rowcount > 0
    
    def cleanup_expired_tasks(self, current_time: datetime) -> int:
        """Synchronously clean up expired tasks based on TTL."""
        current_timestamp = current_time.timestamp()
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tasks WHERE ttl_timestamp IS NOT NULL AND ttl_timestamp < ?', (current_timestamp,))
                conn.commit()
                return cursor.rowcount
    
    async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired tasks based on TTL."""
        current_timestamp = current_time.timestamp()
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('DELETE FROM tasks WHERE ttl_timestamp IS NOT NULL AND ttl_timestamp < ?', (current_timestamp,))
                await conn.commit()
                return cursor.rowcount
    
    def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
        """Synchronously update the state of a schedule (active/paused)."""
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO schedules (schedule_id, active) VALUES (?, ?)', (schedule_id, int(active)))
                conn.commit()
                return cursor.rowcount > 0
    
    async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
        """Asynchronously update the state of a schedule (active/paused)."""
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('INSERT OR REPLACE INTO schedules (schedule_id, active) VALUES (?, ?)', (schedule_id, int(active)))
                await conn.commit()
                return cursor.rowcount > 0
    
    def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
        """Synchronously retrieve the state of a schedule (active/paused)."""
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT active FROM schedules WHERE schedule_id = ?', (schedule_id,))
            result = cursor.fetchone()
            if result is not None:
                return bool(result[0])
            return None
    
    async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
        """Asynchronously retrieve the state of a schedule (active/paused)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT active FROM schedules WHERE schedule_id = ?', (schedule_id,))
            result = await cursor.fetchone()
            if result is not None:
                return bool(result[0])
            return None
    
    def store_result(self, result: TaskResult) -> None:
        """Synchronously store a task result in the backend."""
        serialized = self.serializer.serialize(result)
        ttl_timestamp = None
        if result.ttl is not None:
            ttl_timestamp = (result.completed_at.timestamp() + result.ttl) if result.completed_at else datetime.now().timestamp() + result.ttl
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO results (task_id, serialized_data, serialization_format, ttl_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (result.task_id, serialized['data'], serialized['__serialization_format__'].decode('utf-8'), 
                      ttl_timestamp, result.completed_at.timestamp() if result.completed_at else datetime.now().timestamp()))
                conn.commit()
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Asynchronously store a task result in the backend."""
        serialized = self.serializer.serialize(result)
        ttl_timestamp = None
        if result.ttl is not None:
            ttl_timestamp = (result.completed_at.timestamp() + result.ttl) if result.completed_at else datetime.now().timestamp() + result.ttl
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                await conn.execute('''
                    INSERT OR REPLACE INTO results (task_id, serialized_data, serialization_format, ttl_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (result.task_id, serialized['data'], serialized['__serialization_format__'].decode('utf-8'), 
                      ttl_timestamp, result.completed_at.timestamp() if result.completed_at else datetime.now().timestamp()))
                await conn.commit()
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Synchronously retrieve a task result by task ID."""
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM results WHERE task_id = ?', (task_id,))
            result = cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, TaskResult)
            return None
    
    async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
        """Asynchronously retrieve a task result by task ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM results WHERE task_id = ?', (task_id,))
            result = await cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, TaskResult)
            return None
    
    def get_results(self, limit: int = 100) -> List[TaskResult]:
        """Synchronously retrieve a list of task results, optionally limited."""
        results = []
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM results ORDER BY created_at DESC LIMIT ?', (limit,))
            for row in cursor.fetchall():
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                results.append(self.serializer.deserialize(serialized_data, TaskResult))
        return results
    
    async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
        """Asynchronously retrieve a list of task results, optionally limited."""
        results = []
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM results ORDER BY created_at DESC LIMIT ?', (limit,))
            rows = await cursor.fetchall()
            for row in rows:
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                results.append(self.serializer.deserialize(serialized_data, TaskResult))
        return results
    
    def delete_result(self, task_id: str) -> bool:
        """Synchronously delete a task result by task ID."""
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM results WHERE task_id = ?', (task_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    async def delete_result_async(self, task_id: str) -> bool:
        """Asynchronously delete a task result by task ID."""
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('DELETE FROM results WHERE task_id = ?', (task_id,))
                await conn.commit()
                return cursor.rowcount > 0
    
    def cleanup_expired_results(self, current_time: datetime) -> int:
        """Synchronously clean up expired results based on TTL."""
        current_timestamp = current_time.timestamp()
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM results WHERE ttl_timestamp IS NOT NULL AND ttl_timestamp < ?', (current_timestamp,))
                conn.commit()
                return cursor.rowcount
    
    async def cleanup_expired_results_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired results based on TTL."""
        current_timestamp = current_time.timestamp()
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('DELETE FROM results WHERE ttl_timestamp IS NOT NULL AND ttl_timestamp < ?', (current_timestamp,))
                await conn.commit()
                return cursor.rowcount
