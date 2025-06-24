"""SQLite storage backend for events in OmniQ."""

import sqlite3
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading
import asyncio
from contextlib import contextmanager, asynccontextmanager

from omniq.models.task_event import TaskEvent
from omniq.storage.base import BaseEventStorage
from omniq.serialization.manager import SerializationManager


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
