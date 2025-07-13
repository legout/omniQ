"""SQLite event storage implementation."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite

from ..config.loader import LoggingConfig
from ..models.event import TaskEvent
from .base import BaseEventStorage


class SQLiteEventStorage(BaseEventStorage):
    """SQLite-based event storage supporting both memory and file storage."""
    
    def __init__(
        self,
        database_path: str = ":memory:",
        table_prefix: str = "omniq"
    ):
        """
        Initialize SQLite event storage.
        
        Args:
            database_path: Path to SQLite database or ":memory:" for in-memory
            table_prefix: Prefix for database tables
        """
        self.database_path = database_path
        self.table_prefix = table_prefix
        self.events_table = f"{table_prefix}_events"
        
        self._db: Optional[aiosqlite.Connection] = None
        self._logger = LoggingConfig.get_logger("storage.sqlite.events")
        
        # For event streaming
        self._event_stream_queue: asyncio.Queue = asyncio.Queue()
        self._streaming_active = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._disconnect()
    
    async def _connect(self) -> None:
        """Connect to SQLite database and initialize tables."""
        if self._db is not None:
            return
        
        # Create directory if using file database
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        
        # Enable WAL mode for better concurrency (file databases only)
        if self.database_path != ":memory:":
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA synchronous=NORMAL")
        
        # Create tables
        await self._create_tables()
        
        self._logger.debug(f"Connected to SQLite database: {self.database_path}")
    
    async def _disconnect(self) -> None:
        """Disconnect from SQLite database."""
        if self._db:
            await self._db.close()
            self._db = None
            self._logger.debug("Disconnected from SQLite database")
    
    async def _create_tables(self) -> None:
        """Create database tables."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.events_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            worker_id TEXT,
            worker_type TEXT,
            queue_name TEXT,
            message TEXT,
            details TEXT,
            error_type TEXT,
            error_message TEXT,
            duration_ms REAL,
            memory_mb REAL,
            cpu_time_ms REAL,
            tags TEXT,
            metadata TEXT,
            created_at REAL NOT NULL DEFAULT (unixepoch('subsec'))
        )
        """
        
        # Create indexes separately
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{self.events_table}_task_id ON {self.events_table}(task_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.events_table}_event_type ON {self.events_table}(event_type)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.events_table}_timestamp ON {self.events_table}(timestamp)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.events_table}_worker ON {self.events_table}(worker_id)"
        ]
        
        await self._db.execute(create_table_sql)
        
        # Create indexes
        for index_sql in indexes:
            await self._db.execute(index_sql)
        
        await self._db.commit()
    
    async def store_event(self, event: TaskEvent) -> None:
        """Store a task event."""
        # Convert dict fields to JSON
        details_json = json.dumps(event.details) if event.details else None
        tags_json = json.dumps(event.tags) if event.tags else None
        metadata_json = json.dumps(event.metadata) if event.metadata else None
        
        # Insert event
        insert_sql = f"""
        INSERT INTO {self.events_table}
        (task_id, event_type, timestamp, worker_id, worker_type, queue_name,
         message, details, error_type, error_message, duration_ms, memory_mb,
         cpu_time_ms, tags, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self._db.execute(insert_sql, (
            event.task_id,
            event.event_type.value,
            event.timestamp,
            event.worker_id,
            event.worker_type,
            event.queue_name,
            event.message,
            details_json,
            event.error_type,
            event.error_message,
            event.duration_ms,
            event.memory_mb,
            event.cpu_time_ms,
            tags_json,
            metadata_json
        ))
        await self._db.commit()
        
        # Add to stream queue for real-time streaming
        if self._streaming_active:
            try:
                self._event_stream_queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events if queue is full
        
        self._logger.debug(f"Stored event {event.event_type} for task {event.task_id}")
    
    async def get_events(
        self,
        task_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get events for a specific task."""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""
        
        select_sql = f"""
        SELECT task_id, event_type, timestamp, worker_id, worker_type, queue_name,
               message, details, error_type, error_message, duration_ms, memory_mb,
               cpu_time_ms, tags, metadata
        FROM {self.events_table}
        WHERE task_id = ?
        ORDER BY timestamp ASC
        {limit_clause} {offset_clause}
        """
        
        events = []
        async with self._db.execute(select_sql, (task_id,)) as cursor:
            async for row in cursor:
                event = self._row_to_event(row)
                events.append(event)
        
        return events
    
    async def get_events_by_type(
        self,
        event_type: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get events by type."""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""
        
        select_sql = f"""
        SELECT task_id, event_type, timestamp, worker_id, worker_type, queue_name,
               message, details, error_type, error_message, duration_ms, memory_mb,
               cpu_time_ms, tags, metadata
        FROM {self.events_table}
        WHERE event_type = ?
        ORDER BY timestamp DESC
        {limit_clause} {offset_clause}
        """
        
        events = []
        async with self._db.execute(select_sql, (event_type,)) as cursor:
            async for row in cursor:
                event = self._row_to_event(row)
                events.append(event)
        
        return events
    
    async def list_events(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[TaskEvent]:
        """List events with optional filtering."""
        where_clauses = []
        params = []
        
        if filters:
            if 'task_id' in filters:
                where_clauses.append("task_id = ?")
                params.append(filters['task_id'])
            
            if 'event_type' in filters:
                if isinstance(filters['event_type'], list):
                    placeholders = ','.join('?' * len(filters['event_type']))
                    where_clauses.append(f"event_type IN ({placeholders})")
                    params.extend(filters['event_type'])
                else:
                    where_clauses.append("event_type = ?")
                    params.append(filters['event_type'])
            
            if 'worker_id' in filters:
                where_clauses.append("worker_id = ?")
                params.append(filters['worker_id'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""
        
        select_sql = f"""
        SELECT task_id, event_type, timestamp, worker_id, worker_type, queue_name,
               message, details, error_type, error_message, duration_ms, memory_mb,
               cpu_time_ms, tags, metadata
        FROM {self.events_table}
        {where_clause}
        ORDER BY timestamp DESC
        {limit_clause} {offset_clause}
        """
        
        events = []
        async with self._db.execute(select_sql, params) as cursor:
            async for row in cursor:
                event = self._row_to_event(row)
                events.append(event)
        
        return events
    
    async def count_events(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count events with optional filtering."""
        where_clauses = []
        params = []
        
        if filters:
            if 'task_id' in filters:
                where_clauses.append("task_id = ?")
                params.append(filters['task_id'])
            
            if 'event_type' in filters:
                where_clauses.append("event_type = ?")
                params.append(filters['event_type'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        count_sql = f"""
        SELECT COUNT(*) as count
        FROM {self.events_table}
        {where_clause}
        """
        
        async with self._db.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    async def delete_events(self, task_id: str) -> int:
        """Delete all events for a task."""
        count_sql = f"SELECT COUNT(*) as count FROM {self.events_table} WHERE task_id = ?"
        async with self._db.execute(count_sql, (task_id,)) as cursor:
            row = await cursor.fetchone()
            count = row['count'] if row else 0
        
        delete_sql = f"DELETE FROM {self.events_table} WHERE task_id = ?"
        await self._db.execute(delete_sql, (task_id,))
        await self._db.commit()
        
        return count
    
    async def cleanup_expired_events(self) -> int:
        """Remove expired events and return count."""
        # For now, we don't implement TTL for events in this basic version
        # This would require adding TTL columns and logic
        return 0
    
    async def stream_events(
        self,
        task_id: Optional[str] = None,
        event_types: Optional[List[str]] = None
    ) -> AsyncIterator[TaskEvent]:
        """Stream events in real-time."""
        self._streaming_active = True
        
        try:
            while True:
                try:
                    # Wait for new events
                    event = await asyncio.wait_for(self._event_stream_queue.get(), timeout=1.0)
                    
                    # Apply filters
                    if task_id and event.task_id != task_id:
                        continue
                    
                    if event_types and event.event_type.value not in event_types:
                        continue
                    
                    yield event
                    
                except asyncio.TimeoutError:
                    # Check if we should continue streaming
                    continue
                    
        finally:
            self._streaming_active = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        if self._db is None:
            return {"status": "disconnected"}
        
        try:
            # Test database connection
            async with self._db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            
            # Get statistics
            stats_sql = f"""
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT task_id) as unique_tasks,
                COUNT(DISTINCT event_type) as unique_event_types
            FROM {self.events_table}
            """
            
            async with self._db.execute(stats_sql) as cursor:
                row = await cursor.fetchone()
                stats = dict(row) if row else {}
            
            return {
                "status": "healthy",
                "database_path": self.database_path,
                "table_prefix": self.table_prefix,
                "streaming_active": self._streaming_active,
                **stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _row_to_event(self, row: aiosqlite.Row) -> TaskEvent:
        """Convert database row to TaskEvent object."""
        from ..models.event import TaskEventType
        
        # Parse JSON fields
        details = json.loads(row['details']) if row['details'] else {}
        tags = json.loads(row['tags']) if row['tags'] else {}
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return TaskEvent(
            task_id=row['task_id'],
            event_type=TaskEventType(row['event_type']),
            timestamp=row['timestamp'],
            worker_id=row['worker_id'],
            worker_type=row['worker_type'],
            queue_name=row['queue_name'],
            message=row['message'],
            details=details,
            error_type=row['error_type'],
            error_message=row['error_message'],
            duration_ms=row['duration_ms'],
            memory_mb=row['memory_mb'],
            cpu_time_ms=row['cpu_time_ms'],
            tags=tags,
            metadata=metadata
        )