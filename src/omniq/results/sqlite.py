"""SQLite result storage implementations for OmniQ.

This module provides concrete SQLite-based implementations of the result storage interface:
- AsyncSQLiteResultStorage and SQLiteResultStorage: Result storage with TTL support

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
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
    
    async def _ensure_initialized(self):
        """Ensure the database schema is initialized."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
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
            await db.commit()
        
        self._initialized = True
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        # Calculate expiration time
        expires_at = None
        if result.ttl:
            expires_at = (result.timestamp + result.ttl).isoformat()
        
        # Serialize result data
        result_data_json = msgspec.json.encode(result.result_data).decode()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO results (
                    task_id, status, result_data_json, timestamp, expires_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                str(result.task_id), result.status.value, result_data_json,
                result.timestamp.isoformat(), expires_at
            ))
            await db.commit()
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT status, result_data_json, timestamp, expires_at
                FROM results
                WHERE task_id = ?
            """, (str(task_id),))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            status_str, result_data_json, timestamp_str, expires_at_str = row
            
            # Check if result has expired
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() > expires_at:
                    # Clean up expired result
                    await db.execute("DELETE FROM results WHERE task_id = ?", (str(task_id),))
                    await db.commit()
                    return None
            
            # Deserialize result data
            result_data = msgspec.json.decode(result_data_json.encode())
            timestamp = datetime.fromisoformat(timestamp_str)
            status = TaskStatus(status_str)
            
            # Calculate TTL
            ttl = None
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                ttl = expires_at - timestamp
            
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
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM results WHERE task_id = ?", (str(task_id),))
            await db.commit()
            return cursor.rowcount > 0
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        await self._ensure_initialized()
        
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM results 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            await db.commit()
            return cursor.rowcount
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT task_id, result_data_json, timestamp, expires_at
                FROM results 
                WHERE status = ?
                ORDER BY timestamp DESC
            """, (status,))
            
            async for row in cursor:
                task_id, result_data_json, timestamp_str, expires_at_str = row
                
                # Check if result has expired
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.utcnow() > expires_at:
                        continue
                
                # Deserialize result data
                result_data = msgspec.json.decode(result_data_json.encode())
                timestamp = datetime.fromisoformat(timestamp_str)
                task_status = TaskStatus(status)
                
                # Calculate TTL
                ttl = None
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    ttl = expires_at - timestamp
                
                yield TaskResult(
                    task_id=uuid.UUID(task_id),
                    status=task_status,
                    result_data=result_data,
                    timestamp=timestamp,
                    ttl=ttl
                )


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
        async def _collect_results():
            results = []
            async for result in self.get_results_by_status_async(status):
                results.append(result)
            return results
        
        # Convert async generator to sync iterator
        results = anyio.run(_collect_results)
        return iter(results)

