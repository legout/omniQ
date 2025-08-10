"""SQLite result storage implementations for OmniQ.

This module provides concrete SQLite-based implementations of the result storage interface:
- AsyncSQLiteResultStorage and SQLiteResultStorage: Result storage with TTL support

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import aiosqlite
import anyio
import msgspec

from .base import BaseResultStorage
from ..models.result import TaskResult, TaskStatus


class AsyncSQLiteResultStorage(BaseResultStorage):
    """Async SQLite-based result storage implementation.
    
    Features:
    - TTL support with automatic cleanup
    - Status-based querying
    - Efficient indexing
    """
    
    def __init__(self, db_path: str):
        """Initialize the async SQLite result storage.
        
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
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result_data_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_status
                ON results(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_expires_at
                ON results(expires_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_status_expires_at
                ON results(status, expires_at)
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

    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        # Validate input
        if not result.task_id:
            raise ValueError("Task ID cannot be empty")
        
        # Calculate expiration time
        expires_at = None
        if result.ttl:
            expires_at = (result.timestamp + result.ttl).isoformat()
        
        # Serialize result data with error handling
        try:
            result_data_json = msgspec.json.encode(result.result_data)
        except Exception as e:
            raise ValueError(f"Failed to encode result data: {e}")
        
        db = await self._get_connection()
        try:
            await db.execute("""
                INSERT OR REPLACE INTO results (
                    task_id, status, result_data_json, timestamp, expires_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                str(result.task_id), result.status.value, result_data_json,
                result.timestamp.isoformat(), expires_at
            ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        db = await self._get_connection()
        try:
            # Use a transaction to ensure atomic operations
            await db.execute("BEGIN IMMEDIATE")
            
            cursor = await db.execute("""
                SELECT status, result_data_json, timestamp, expires_at
                FROM results
                WHERE task_id = ?
            """, (str(task_id),))
            
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None
            
            status_str, result_data_json, timestamp_str, expires_at_str = row
            
            # Check if result has expired and delete atomically if it is
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at:
                    # Clean up expired result within the same transaction
                    await db.execute("DELETE FROM results WHERE task_id = ?", (str(task_id),))
                    await db.commit()
                    return None
            
            # Deserialize result data with error handling
            try:
                result_data = msgspec.json.decode(result_data_json)
            except Exception as e:
                await db.rollback()
                raise ValueError(f"Failed to decode result data: {e}")
            
            # Parse timestamp with timezone awareness
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except Exception as e:
                await db.rollback()
                raise ValueError(f"Failed to parse timestamp: {e}")
            
            status = TaskStatus(status_str)
            
            # Calculate TTL
            ttl = None
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                ttl = expires_at - timestamp
            
            await db.commit()
            
            return TaskResult(
                task_id=task_id,
                status=status,
                result_data=result_data,
                timestamp=timestamp,
                ttl=ttl
            )
        except Exception as e:
            await db.rollback()
            raise
    
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously."""
        await self._ensure_initialized()
        
        db = await self._get_connection()
        try:
            cursor = await db.execute("DELETE FROM results WHERE task_id = ?", (str(task_id),))
            await db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            await db.rollback()
            raise
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        await self._ensure_initialized()
        
        now = datetime.now(timezone.utc).isoformat()
        
        db = await self._get_connection()
        try:
            cursor = await db.execute("""
                DELETE FROM results
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            await db.commit()
            return cursor.rowcount
        except Exception as e:
            await db.rollback()
            raise
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        # Validate status
        try:
            TaskStatus(status)  # This will raise ValueError if status is invalid
        except ValueError:
            raise ValueError(f"Invalid status: {status}")
        
        now = datetime.now(timezone.utc).isoformat()
        
        db = await self._get_connection()
        try:
            # Use SQL to filter out expired results efficiently
            cursor = await db.execute("""
                SELECT task_id, result_data_json, timestamp, expires_at
                FROM results
                WHERE status = ? AND (expires_at IS NULL OR expires_at >= ?)
                ORDER BY timestamp DESC
            """, (status, now))
            
            async for row in cursor:
                task_id, result_data_json, timestamp_str, expires_at_str = row
                
                # Deserialize result data with error handling
                try:
                    result_data = msgspec.json.decode(result_data_json)
                except Exception as e:
                    # Skip results that can't be decoded
                    continue
                
                # Parse timestamp with timezone awareness
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                except Exception:
                    # Skip results with invalid timestamps
                    continue
                
                task_status = TaskStatus(status)
                
                # Calculate TTL
                ttl = None
                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        ttl = expires_at - timestamp
                    except Exception:
                        # Skip results with invalid expiration times
                        continue
                
                yield TaskResult(
                    task_id=uuid.UUID(task_id),
                    status=task_status,
                    result_data=result_data,
                    timestamp=timestamp,
                    ttl=ttl
                )
        except Exception as e:
            raise


class SQLiteResultStorage(AsyncSQLiteResultStorage):
    """Synchronous wrapper for AsyncSQLiteResultStorage."""
    
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
        # Create a queue to yield results lazily
        result_queue = anyio.create_queue(10)  # Buffer size of 10
        
        async def _producer():
            try:
                async for result in self.get_results_by_status_async(status):
                    await result_queue.put(result)
            finally:
                await result_queue.put(None)  # Signal end
        
        async def _consumer():
            # Start the producer task
            async with anyio.create_task_group() as tg:
                tg.start_soon(_producer)
                
                while True:
                    result = await result_queue.get()
                    if result is None:  # End signal
                        break
                    yield result
        
        # Convert async generator to sync iterator using anyio
        return anyio.run(_consumer).__iter__()

