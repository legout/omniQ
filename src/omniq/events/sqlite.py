"""SQLite event storage implementations for OmniQ.

This module provides concrete SQLite-based implementations of the event storage interface:
- AsyncSQLiteEventStorage and SQLiteEventStorage: Event logging storage

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime
from typing import Optional, List, AsyncIterator, Iterator

import aiosqlite
import anyio

from .base import BaseEventStorage
from ..models.event import TaskEvent, TaskEventType


class AsyncSQLiteEventStorage(BaseEventStorage):
    """Async SQLite-based event storage implementation.
    
    Features:
    - Structured event logging
    - Time-range queries
    - Event type filtering
    - Automatic cleanup
    """
    
    def __init__(self, db_path: str):
        """Initialize the async SQLite event storage.
        
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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    worker_id TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task_id
                ON events(task_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_event_type
                ON events(event_type)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            """)
            await db.commit()
        
        self._initialized = True
    
    async def log_event_async(self, event: TaskEvent) -> None:
        """Log a task event asynchronously."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO events (task_id, event_type, timestamp, worker_id)
                VALUES (?, ?, ?, ?)
            """, (
                str(event.task_id), event.event_type.value,
                event.timestamp.isoformat(), event.worker_id
            ))
            await db.commit()
    
    async def get_events_async(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Get all events for a task asynchronously."""
        await self._ensure_initialized()
        
        events = []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT event_type, timestamp, worker_id
                FROM events
                WHERE task_id = ?
                ORDER BY timestamp ASC
            """, (str(task_id),))
            
            async for row in cursor:
                event_type_str, timestamp_str, worker_id = row
                events.append(TaskEvent(
                    task_id=task_id,
                    event_type=TaskEventType(event_type_str),
                    timestamp=datetime.fromisoformat(timestamp_str),
                    worker_id=worker_id
                ))
        
        return events
    
    async def get_events_by_type_async(self, event_type: str, limit: Optional[int] = None) -> AsyncIterator[TaskEvent]:
        """Get events by type asynchronously."""
        await self._ensure_initialized()
        
        query = """
            SELECT task_id, timestamp, worker_id
            FROM events 
            WHERE event_type = ?
            ORDER BY timestamp DESC
        """
        params = [event_type]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            
            async for row in cursor:
                task_id, timestamp_str, worker_id = row
                yield TaskEvent(
                    task_id=uuid.UUID(task_id),
                    event_type=TaskEventType(event_type),
                    timestamp=datetime.fromisoformat(timestamp_str),
                    worker_id=worker_id
                )
    
    async def get_events_in_range_async(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[TaskEvent]:
        """Get events within a time range asynchronously."""
        await self._ensure_initialized()
        
        query = """
            SELECT task_id, event_type, timestamp, worker_id
            FROM events
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if task_id:
            query += " AND task_id = ?"
            params.append(str(task_id))
        
        query += " ORDER BY timestamp ASC"
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            
            async for row in cursor:
                task_id_val, event_type_str, timestamp_str, worker_id = row
                yield TaskEvent(
                    task_id=uuid.UUID(task_id_val),
                    event_type=TaskEventType(event_type_str),
                    timestamp=datetime.fromisoformat(timestamp_str),
                    worker_id=worker_id
                )
    
    async def cleanup_old_events_async(self, older_than: datetime) -> int:
        """Clean up old events asynchronously."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM events 
                WHERE timestamp < ?
            """, (older_than.isoformat(),))
            await db.commit()
            return cursor.rowcount


class SQLiteEventStorage(AsyncSQLiteEventStorage):
    """Synchronous wrapper for AsyncSQLiteEventStorage."""
    
    def log_event(self, event: TaskEvent) -> None:
        """Synchronous wrapper for log_event_async."""
        anyio.run(self.log_event_async, event)
    
    def get_events(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_async."""
        return anyio.run(self.get_events_async, task_id)
    
    def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_by_type_async."""
        async def _collect_events():
            events = []
            async for event in self.get_events_by_type_async(event_type, limit):
                events.append(event)
            return events
        
        # Convert async generator to sync iterator
        events = anyio.run(_collect_events)
        return iter(events)
    
    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_in_range_async."""
        async def _collect_events():
            events = []
            async for event in self.get_events_in_range_async(start_time, end_time, task_id):
                events.append(event)
            return events
        
        # Convert async generator to sync iterator
        events = anyio.run(_collect_events)
        return iter(events)
    
    def cleanup_old_events(self, older_than: datetime) -> int:
        """Synchronous wrapper for cleanup_old_events_async."""
        return anyio.run(self.cleanup_old_events_async, older_than)