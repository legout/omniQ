"""PostgreSQL result storage implementations for OmniQ.

This module provides concrete PostgreSQL-based implementations of the result storage interface:
- AsyncPostgresResultStorage and PostgresResultStorage: Result storage with TTL support using asyncpg

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import anyio
import asyncpg
import msgspec

from .base import BaseResultStorage
from ..models.result import TaskResult, TaskStatus


class AsyncPostgresResultStorage(BaseResultStorage):
    """Async PostgreSQL-based result storage implementation.
    
    Features:
    - TTL support with automatic cleanup
    - Status-based querying
    - Persistent storage with PostgreSQL
    - Connection pooling for efficiency
    """
    
    def __init__(
        self,
        dsn: str,
        table_name: str = "omniq_results",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the async PostgreSQL result storage.
        
        Args:
            dsn: PostgreSQL connection string
            table_name: Name of the results table
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
                    task_id UUID PRIMARY KEY,
                    status VARCHAR(20) NOT NULL,
                    result_data JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    INDEX (status, timestamp),
                    INDEX (expires_at)
                )
            """)
        
        self._initialized = True
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        # Calculate expiration time
        expires_at = None
        if result.ttl:
            expires_at = result.timestamp + result.ttl
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} 
                (task_id, status, result_data, timestamp, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    result_data = EXCLUDED.result_data,
                    timestamp = EXCLUDED.timestamp,
                    expires_at = EXCLUDED.expires_at
                """,
                result.task_id,
                result.status.value,
                msgspec.json.encode(result.result_data),
                result.timestamp,
                expires_at
            )
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT task_id, status, result_data, timestamp, expires_at
                FROM {self.table_name}
                WHERE task_id = $1
                """,
                task_id
            )
            
            if not row:
                return None
            
            # Check if result has expired
            if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                # Clean up expired result
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE task_id = $1",
                    task_id
                )
                return None
            
            # Reconstruct the result
            result_data = msgspec.json.decode(row['result_data']) if row['result_data'] else None
            timestamp = row['timestamp']
            status = TaskStatus(row['status'])
            
            # Calculate TTL
            ttl = None
            if row['expires_at']:
                ttl = row['expires_at'] - timestamp
            
            return TaskResult(
                task_id=task_id,
                status=status,
                result_data=result_data,
                timestamp=timestamp,
                ttl=ttl
            )
    
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE task_id = $1",
                task_id
            )
            return "DELETE 1" in result
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE expires_at < NOW()"
            )
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[1]) if " " in result else 0
            return count
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        async with self.pool.acquire() as conn:
            # Get all results with the specified status
            rows = await conn.fetch(
                f"""
                SELECT task_id, status, result_data, timestamp, expires_at
                FROM {self.table_name}
                WHERE status = $1 AND (expires_at IS NULL OR expires_at >= NOW())
                ORDER BY timestamp DESC
                """,
                status
            )
            
            for row in rows:
                # Skip expired results (double-check)
                if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                    continue
                
                # Reconstruct the result
                result_data = msgspec.json.decode(row['result_data']) if row['result_data'] else None
                task_status = TaskStatus(row['status'])
                timestamp = row['timestamp']
                
                # Calculate TTL
                ttl = None
                if row['expires_at']:
                    ttl = row['expires_at'] - timestamp
                
                yield TaskResult(
                    task_id=row['task_id'],
                    status=task_status,
                    result_data=result_data,
                    timestamp=timestamp,
                    ttl=ttl
                )
    
    async def close_async(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False


class PostgresResultStorage(AsyncPostgresResultStorage):
    """Synchronous wrapper for AsyncPostgresResultStorage."""
    
    def store_result(self, result: TaskResult) -> None:
        """Synchronous wrapper for store_result_async."""
        anyio.run(self.store_result_async, result)
    
    def get_result(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Synchronous wrapper for get_result_async."""
        return anyio.run(self.get_result_async, task_id)
    
    def delete_result(self, task_id: uuid.UUID) -> bool:
        """Synchronous wrapper for delete_result_async."""
        return anyio.run(self.delete_result_async, task_id)
    
    def cleanup_expired(self) -> int:
        """Synchronous wrapper for cleanup_expired_async."""
        return anyio.run(self.cleanup_expired_async)
    
    def get_results_by_status(self, status: str) -> Iterator[TaskResult]:
        """Synchronous wrapper for get_results_by_status_async."""
        async def _collect_results():
            results = []
            async for result in self.get_results_by_status_async(status):
                results.append(result)
            return results
        
        # Convert async generator to sync iterator
        results = anyio.run(_collect_results)
        return iter(results)
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        anyio.run(self.close_async)
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()