"""SQLite event storage implementations for OmniQ.

This module provides concrete SQLite-based implementations of the event storage interface:
- AsyncSQLiteEventStorage and SQLiteEventStorage: Event logging storage

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, AsyncIterator, Iterator
import logging

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
    - Connection pooling
    - Robust error handling
    """
    
    def __init__(self, db_path: str):
        """Initialize the async SQLite event storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
        self._conn: Optional[aiosqlite.Connection] = None
        self._conn_lock = anyio.Lock()
    
    async def _ensure_initialized(self):
        """Ensure the database schema is initialized."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
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
            # Add composite indexes for common query patterns
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task_id_timestamp
                ON events(task_id, timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_event_type_timestamp
                ON events(event_type, timestamp)
            """)
            await db.commit()
        
        self._initialized = True
        
        # TODO: Implement schema versioning mechanism for future migrations
        # This should include:
        # - A schema_version table to track current schema version
        # - Migration functions to handle schema changes
        # - Version checking and upgrade logic in _ensure_initialized
    
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
    
    async def log_event_async(self, event: TaskEvent) -> None:
        """Log a task event asynchronously."""
        await self._ensure_initialized()
        
        # Validate input data
        if not event.task_id:
            raise ValueError("Task ID cannot be empty")
        if not event.event_type:
            raise ValueError("Event type cannot be empty")
        if not event.timestamp:
            raise ValueError("Timestamp cannot be empty")
        
        # Ensure timestamp is timezone-aware UTC
        if event.timestamp.tzinfo is None:
            timestamp = event.timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = event.timestamp.astimezone(timezone.utc)
        
        db = await self._get_connection()
        try:
            await db.execute("""
                INSERT INTO events (task_id, event_type, timestamp, worker_id)
                VALUES (?, ?, ?, ?)
            """, (
                str(event.task_id), event.event_type.value,
                timestamp.isoformat(), event.worker_id
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to log event: {e}")
            raise
    
    async def get_events_async(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Get all events for a task asynchronously."""
        await self._ensure_initialized()
        
        # Validate input
        if not task_id:
            raise ValueError("Task ID cannot be empty")
        
        events = []
        db = await self._get_connection()
        try:
            # Use transaction with immediate lock for consistency
            await db.execute("BEGIN IMMEDIATE")
            
            cursor = await db.execute("""
                SELECT event_type, timestamp, worker_id
                FROM events
                WHERE task_id = ?
                ORDER BY timestamp ASC
            """, (str(task_id),))
            
            async for row in cursor:
                event_type_str, timestamp_str, worker_id = row
                
                # Handle TaskEventType conversion with error handling
                try:
                    event_type = TaskEventType(event_type_str)
                except ValueError as e:
                    logging.warning(f"Invalid event type '{event_type_str}' for task {task_id}: {e}")
                    continue
                
                # Handle timestamp parsing with error handling
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    logging.warning(f"Invalid timestamp '{timestamp_str}' for task {task_id}: {e}")
                    continue
                
                events.append(TaskEvent(
                    task_id=task_id,
                    event_type=event_type,
                    timestamp=timestamp,
                    worker_id=worker_id
                ))
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to get events for task {task_id}: {e}")
            raise
        
        return events
    
    async def get_events_by_type_async(self, event_type: str, limit: Optional[int] = None) -> AsyncIterator[TaskEvent]:
        """Get events by type asynchronously."""
        await self._ensure_initialized()
        
        # Validate input
        if not event_type:
            raise ValueError("Event type cannot be empty")
        
        # Validate event type
        try:
            TaskEventType(event_type)  # This will raise ValueError if invalid
        except ValueError:
            raise ValueError(f"Invalid event type: {event_type}")
        
        if limit is not None and limit <= 0:
            raise ValueError("Limit must be positive or None")
        
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
        
        db = await self._get_connection()
        try:
            # Use transaction with immediate lock for consistency
            await db.execute("BEGIN IMMEDIATE")
            
            cursor = await db.execute(query, params)
            
            async for row in cursor:
                task_id_str, timestamp_str, worker_id = row
                
                # Handle UUID conversion with error handling
                try:
                    task_id = uuid.UUID(task_id_str)
                except ValueError as e:
                    logging.warning(f"Invalid task ID '{task_id_str}': {e}")
                    continue
                
                # Handle timestamp parsing with error handling
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    logging.warning(f"Invalid timestamp '{timestamp_str}': {e}")
                    continue
                
                yield TaskEvent(
                    task_id=task_id,
                    event_type=TaskEventType(event_type),
                    timestamp=timestamp,
                    worker_id=worker_id
                )
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to get events by type '{event_type}': {e}")
            raise
    
    async def get_events_in_range_async(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[TaskEvent]:
        """Get events within a time range asynchronously."""
        await self._ensure_initialized()
        
        # Validate input
        if not start_time:
            raise ValueError("Start time cannot be empty")
        if not end_time:
            raise ValueError("End time cannot be empty")
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")
        
        # Ensure timestamps are timezone-aware UTC
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = start_time.astimezone(timezone.utc)
            
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        else:
            end_time = end_time.astimezone(timezone.utc)
        
        query = """
            SELECT task_id, event_type, timestamp, worker_id
            FROM events
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if task_id:
            if not task_id:
                raise ValueError("Task ID cannot be empty")
            query += " AND task_id = ?"
            params.append(str(task_id))
        
        query += " ORDER BY timestamp ASC"
        
        db = await self._get_connection()
        try:
            # Use transaction with immediate lock for consistency
            await db.execute("BEGIN IMMEDIATE")
            
            cursor = await db.execute(query, params)
            
            async for row in cursor:
                task_id_str, event_type_str, timestamp_str, worker_id = row
                
                # Handle UUID conversion with error handling
                try:
                    task_id_val = uuid.UUID(task_id_str)
                except ValueError as e:
                    logging.warning(f"Invalid task ID '{task_id_str}': {e}")
                    continue
                
                # Handle TaskEventType conversion with error handling
                try:
                    event_type = TaskEventType(event_type_str)
                except ValueError as e:
                    logging.warning(f"Invalid event type '{event_type_str}': {e}")
                    continue
                
                # Handle timestamp parsing with error handling
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    logging.warning(f"Invalid timestamp '{timestamp_str}': {e}")
                    continue
                
                yield TaskEvent(
                    task_id=task_id_val,
                    event_type=event_type,
                    timestamp=timestamp,
                    worker_id=worker_id
                )
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to get events in range: {e}")
            raise
    
    async def cleanup_old_events_async(self, older_than: datetime) -> int:
        """Clean up old events asynchronously."""
        await self._ensure_initialized()
        
        # Validate input
        if not older_than:
            raise ValueError("Older than time cannot be empty")
        
        # Ensure timestamp is timezone-aware UTC
        if older_than.tzinfo is None:
            older_than = older_than.replace(tzinfo=timezone.utc)
        else:
            older_than = older_than.astimezone(timezone.utc)
        
        db = await self._get_connection()
        try:
            # Use transaction with immediate lock for consistency
            await db.execute("BEGIN IMMEDIATE")
            
            cursor = await db.execute("""
                DELETE FROM events
                WHERE timestamp < ?
            """, (older_than.isoformat(),))
            
            await db.commit()
            return cursor.rowcount
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to cleanup old events: {e}")
            raise


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
        # Create a queue to yield results lazily
        result_queue = anyio.create_queue(10)  # Buffer size of 10
        
        async def _producer():
            try:
                async for event in self.get_events_by_type_async(event_type, limit):
                    await result_queue.put(event)
            finally:
                await result_queue.put(None)  # Signal end
        
        async def _consumer():
            # Start the producer task
            async with anyio.create_task_group() as tg:
                tg.start_soon(_producer)
                
                while True:
                    event = await result_queue.get()
                    if event is None:  # End signal
                        break
                    yield event
        
        # Convert async generator to sync iterator using anyio
        return anyio.run(_consumer).__iter__()
    
    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_in_range_async."""
        # Create a queue to yield results lazily
        result_queue = anyio.create_queue(10)  # Buffer size of 10
        
        async def _producer():
            try:
                async for event in self.get_events_in_range_async(start_time, end_time, task_id):
                    await result_queue.put(event)
            finally:
                await result_queue.put(None)  # Signal end
        
        async def _consumer():
            # Start the producer task
            async with anyio.create_task_group() as tg:
                tg.start_soon(_producer)
                
                while True:
                    event = await result_queue.get()
                    if event is None:  # End signal
                        break
                    yield event
        
        # Convert async generator to sync iterator using anyio
        return anyio.run(_consumer).__iter__()
    
    def cleanup_old_events(self, older_than: datetime) -> int:
        """Synchronous wrapper for cleanup_old_events_async."""
        return anyio.run(self.cleanup_old_events_async, older_than)