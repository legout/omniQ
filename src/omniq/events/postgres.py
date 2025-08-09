"""PostgreSQL event storage implementations for OmniQ.

This module provides concrete PostgreSQL-based implementations of the event storage interface:
- AsyncPostgresEventStorage and PostgresEventStorage: Event storage using asyncpg

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import anyio
import asyncpg
import msgspec

from .base import BaseEventStorage
from ..models.event import TaskEvent, TaskEventType


class AsyncPostgresEventStorage(BaseEventStorage):
    """Async PostgreSQL-based event storage implementation.
    
    Features:
    - Persistent event storage with PostgreSQL
    - Time-based querying and cleanup
    - Event type filtering
    - Connection pooling for efficiency
    """
    
    def __init__(
        self,
        dsn: str,
        table_name: str = "omniq_events",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the async PostgreSQL event storage.
        
        Args:
            dsn: PostgreSQL connection string
            table_name: Name of the events table
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
                    id SERIAL PRIMARY KEY,
                    task_id UUID NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    worker_id VARCHAR(255),
                    INDEX (task_id, timestamp),
                    INDEX (event_type, timestamp),
                    INDEX (timestamp)
                )
            """)
        
        self._initialized = True
    
    async def log_event_async(self, event: TaskEvent) -> None:
        """Log a task event asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} 
                (task_id, event_type, timestamp, worker_id)
                VALUES ($1, $2, $3, $4)
                """,
                event.task_id,
                event.event_type.value,
                event.timestamp,
                event.worker_id
            )
    
    async def get_events_async(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Get all events for a task asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT task_id, event_type, timestamp, worker_id
                FROM {self.table_name}
                WHERE task_id = $1
                ORDER BY timestamp ASC
                """,
                task_id
            )
            
            events = []
            for row in rows:
                events.append(TaskEvent(
                    task_id=row['task_id'],
                    event_type=TaskEventType(row['event_type']),
                    timestamp=row['timestamp'],
                    worker_id=row['worker_id']
                ))
            
            return events
    
    async def get_events_by_type_async(self, event_type: str, limit: Optional[int] = None) -> AsyncIterator[TaskEvent]:
        """Get events by type asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            # Build query with optional limit
            if limit:
                query = f"""
                    SELECT task_id, event_type, timestamp, worker_id
                    FROM {self.table_name}
                    WHERE event_type = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """
                params = [event_type, limit]
            else:
                query = f"""
                    SELECT task_id, event_type, timestamp, worker_id
                    FROM {self.table_name}
                    WHERE event_type = $1
                    ORDER BY timestamp DESC
                """
                params = [event_type]
            
            # Stream results to avoid loading all events into memory at once
            # For PostgreSQL, we'll fetch in batches
            batch_size = 1000
            offset = 0
            
            while True:
                batch_query = query + f" OFFSET {offset} LIMIT {batch_size}"
                if limit:
                    # Adjust batch size if we're approaching the limit
                    remaining = limit - offset
                    if remaining <= 0:
                        break
                    batch_size = min(batch_size, remaining)
                    batch_query = query + f" OFFSET {offset} LIMIT {batch_size}"
                
                rows = await conn.fetch(batch_query, *params)
                
                if not rows:
                    break
                
                for row in rows:
                    yield TaskEvent(
                        task_id=row['task_id'],
                        event_type=TaskEventType(row['event_type']),
                        timestamp=row['timestamp'],
                        worker_id=row['worker_id']
                    )
                
                offset += len(rows)
                
                # If we got fewer rows than batch_size, we're done
                if len(rows) < batch_size:
                    break
    
    async def get_events_in_range_async(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[TaskEvent]:
        """Get events within a time range asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            # Build query with optional task_id filter
            if task_id:
                query = f"""
                    SELECT task_id, event_type, timestamp, worker_id
                    FROM {self.table_name}
                    WHERE timestamp >= $1 AND timestamp <= $2 AND task_id = $3
                    ORDER BY timestamp ASC
                """
                params = [start_time, end_time, task_id]
            else:
                query = f"""
                    SELECT task_id, event_type, timestamp, worker_id
                    FROM {self.table_name}
                    WHERE timestamp >= $1 AND timestamp <= $2
                    ORDER BY timestamp ASC
                """
                params = [start_time, end_time]
            
            # Stream results in batches
            batch_size = 1000
            offset = 0
            
            while True:
                batch_query = query + f" OFFSET {offset} LIMIT {batch_size}"
                rows = await conn.fetch(batch_query, *params)
                
                if not rows:
                    break
                
                for row in rows:
                    yield TaskEvent(
                        task_id=row['task_id'],
                        event_type=TaskEventType(row['event_type']),
                        timestamp=row['timestamp'],
                        worker_id=row['worker_id']
                    )
                
                offset += len(rows)
                
                # If we got fewer rows than batch_size, we're done
                if len(rows) < batch_size:
                    break
    
    async def cleanup_old_events_async(self, older_than: datetime) -> int:
        """Clean up old events asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE timestamp < $1",
                older_than
            )
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[1]) if " " in result else 0
            return count
    
    async def close_async(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False


class PostgresEventStorage(AsyncPostgresEventStorage):
    """Synchronous wrapper for AsyncPostgresEventStorage."""
    
    def log_event(self, event: TaskEvent) -> None:
        """Synchronous wrapper for log_event_async."""
        anyio.run(self.log_event_async, event)
    
    def get_events(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_async."""
        return anyio.run(self.get_events_async, task_id)
    
    def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_by_type_async."""
        async def _collect_results():
            results = []
            async for event in self.get_events_by_type_async(event_type, limit):
                results.append(event)
            return results
        
        # Convert async generator to sync iterator
        results = anyio.run(_collect_results)
        return iter(results)
    
    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_in_range_async."""
        async def _collect_results():
            results = []
            async for event in self.get_events_in_range_async(start_time, end_time, task_id):
                results.append(event)
            return results
        
        # Convert async generator to sync iterator
        results = anyio.run(_collect_results)
        return iter(results)
    
    def cleanup_old_events(self, older_than: datetime) -> int:
        """Synchronous wrapper for cleanup_old_events_async."""
        return anyio.run(self.cleanup_old_events_async, older_than)
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        anyio.run(self.close_async)
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()