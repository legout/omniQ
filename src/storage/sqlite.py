"""SQLite storage backend for tasks, results, and events in OmniQ."""

import sqlite3
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading
import asyncio
from contextlib import contextmanager, asynccontextmanager

from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.models.task_event import TaskEvent
from omniq.storage.base import BaseTaskStorage, BaseResultStorage, BaseEventStorage
from omniq.serialization.manager import SerializationManager


class SQLiteTaskStorage(BaseTaskStorage):
    """SQLite storage backend for tasks with sync and async methods."""
    
    def __init__(self, db_path: str, serializer: Optional[SerializationManager] = None):
        """
        Initialize the SQLite task storage backend.
        
        Args:
            db_path (str): Path to the SQLite database file.
            serializer (Optional[SerializationManager]): Serialization manager for tasks.
        """
        self.db_path = db_path
        self.serializer = serializer or SerializationManager()
        self._init_db()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
    def _init_db(self) -> None:
        """Initialize the database schema with a table for tasks."""
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
            # Schedules table for state management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    active INTEGER NOT NULL
                )
            ''')
            # Index for efficient querying and cleanup
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_ttl ON tasks(ttl_timestamp)')
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


class SQLiteResultStorage(BaseResultStorage):
    """SQLite storage backend for results with sync and async methods."""
    
    def __init__(self, db_path: str, serializer: Optional[SerializationManager] = None):
        """
        Initialize the SQLite result storage backend.
        
        Args:
            db_path (str): Path to the SQLite database file.
            serializer (Optional[SerializationManager]): Serialization manager for results.
        """
        self.db_path = db_path
        self.serializer = serializer or SerializationManager()
        self._init_db()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
    def _init_db(self) -> None:
        """Initialize the database schema with a table for results."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
            # Index for efficient querying and cleanup
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


class SQLiteEventStorage(BaseEventStorage):
    """SQLite storage backend for events with sync and async methods."""
    
    def __init__(self, db_path: str, serializer: Optional[SerializationManager] = None):
        """
        Initialize the SQLite event storage backend.
        
        Args:
            db_path (str): Path to the SQLite database file.
            serializer (Optional[SerializationManager]): Serialization manager for events.
        """
        self.db_path = db_path
        self.serializer = serializer or SerializationManager()
        self._init_db()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
    def _init_db(self) -> None:
        """Initialize the database schema with a table for events."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    serialized_data BLOB NOT NULL,
                    serialization_format TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')
            # Index for efficient querying by task_id and timestamp
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)')
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
    
    def log_event(self, event: TaskEvent) -> None:
        """Synchronously log an event to the storage backend."""
        serialized = self.serializer.serialize(event)
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (event_id, task_id, event_type, serialized_data, serialization_format, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (event.id, event.task_id, event.event_type, serialized['data'], 
                      serialized['__serialization_format__'].decode('utf-8'), event.timestamp))
                conn.commit()
    
    async def log_event_async(self, event: TaskEvent) -> None:
        """Asynchronously log an event to the storage backend."""
        serialized = self.serializer.serialize(event)
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                await conn.execute('''
                    INSERT INTO events (event_id, task_id, event_type, serialized_data, serialization_format, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (event.id, event.task_id, event.event_type, serialized['data'], 
                      serialized['__serialization_format__'].decode('utf-8'), event.timestamp))
                await conn.commit()
    
    def get_event(self, event_id: str) -> Optional[TaskEvent]:
        """Synchronously retrieve an event by ID."""
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM events WHERE event_id = ?', (event_id,))
            result = cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, TaskEvent)
            return None
    
    async def get_event_async(self, event_id: str) -> Optional[TaskEvent]:
        """Asynchronously retrieve an event by ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM events WHERE event_id = ?', (event_id,))
            result = await cursor.fetchone()
            if result:
                serialized_data = {
                    '__serialization_format__': result[1].encode('utf-8'),
                    'data': result[0]
                }
                return self.serializer.deserialize(serialized_data, TaskEvent)
            return None
    
    def get_events_by_task(self, task_id: str, limit: int = 100) -> List[TaskEvent]:
        """Synchronously retrieve events for a specific task, optionally limited."""
        events = []
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM events WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?', (task_id, limit))
            for row in cursor.fetchall():
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    async def get_events_by_task_async(self, task_id: str, limit: int = 100) -> List[TaskEvent]:
        """Asynchronously retrieve events for a specific task, optionally limited."""
        events = []
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM events WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?', (task_id, limit))
            rows = await cursor.fetchall()
            for row in rows:
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[TaskEvent]:
        """Synchronously retrieve events of a specific type, optionally limited."""
        events = []
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT serialized_data, serialization_format FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?', (event_type, limit))
            for row in cursor.fetchall():
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    async def get_events_by_type_async(self, event_type: str, limit: int = 100) -> List[TaskEvent]:
        """Asynchronously retrieve events of a specific type, optionally limited."""
        events = []
        async with self._get_async_connection() as conn:
            cursor = await conn.execute('SELECT serialized_data, serialization_format FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?', (event_type, limit))
            rows = await cursor.fetchall()
            for row in rows:
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    def get_events(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Synchronously retrieve events, optionally filtered by task ID or event type."""
        events = []
        query = 'SELECT serialized_data, serialization_format FROM events'
        params = []
        conditions = []
        if task_id is not None:
            conditions.append('task_id = ?')
            params.append(task_id)
        if event_type is not None:
            conditions.append('event_type = ?')
            params.append(event_type)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        with self._get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    async def get_events_async(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Asynchronously retrieve events, optionally filtered by task ID or event type."""
        events = []
        query = 'SELECT serialized_data, serialization_format FROM events'
        params = []
        conditions = []
        if task_id is not None:
            conditions.append('task_id = ?')
            params.append(task_id)
        if event_type is not None:
            conditions.append('event_type = ?')
            params.append(event_type)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            for row in rows:
                serialized_data = {
                    '__serialization_format__': row[1].encode('utf-8'),
                    'data': row[0]
                }
                events.append(self.serializer.deserialize(serialized_data, TaskEvent))
        return events
    
    def cleanup_old_events(self, retention_days: int) -> int:
        """Synchronously clean up old events based on retention policy."""
        before_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        with self._get_sync_connection() as conn:
            with self._lock:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM events WHERE timestamp < ?', (before_time,))
                conn.commit()
                return cursor.rowcount
    
    async def cleanup_old_events_async(self, retention_days: int) -> int:
        """Asynchronously clean up old events based on retention policy."""
        before_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        async with self._get_async_connection() as conn:
            async with self._async_lock:
                cursor = await conn.execute('DELETE FROM events WHERE timestamp < ?', (before_time,))
                await conn.commit()
                return cursor.rowcount
