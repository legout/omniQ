"""SQLite backend implementation for OmniQ.

This module provides the SQLiteBackend class that acts as a factory
for creating SQLite-based storage component instances.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import aiosqlite
import anyio

from .base import BaseBackend
from ..results.base import BaseResultStorage
from ..queue.base import BaseQueue
from ..events.base import BaseEventStorage
from ..results.sqlite import (
    AsyncSQLiteResultStorage, SQLiteResultStorage
)
from ..queue.sqlite import (
    AsyncSQLiteQueue, SQLiteQueue
)
from ..events.sqlite import (
    AsyncSQLiteEventStorage, SQLiteEventStorage
)


class SQLiteBackend(BaseBackend):
    """SQLite backend implementation.
    
    This backend creates and manages SQLite-based storage components.
    All components share the same database file for efficiency.
    
    Configuration options:
    - db_path: Path to the SQLite database file (required)
    - create_dirs: Whether to create parent directories if they don't exist (default: True)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SQLite backend.
        
        Args:
            config: Configuration dictionary with the following keys:
                - db_path (str): Path to the SQLite database file
                - create_dirs (bool, optional): Create parent directories if needed
        
        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(config)
        
        if "db_path" not in config:
            raise ValueError("SQLite backend requires 'db_path' in configuration")
        
        self.db_path = config["db_path"]
        self.create_dirs = config.get("create_dirs", True)
        self._initialized = False
        self._init_lock = anyio.Lock()
        
        # Storage component instances (created lazily)
        self._queue = None
        self._result_storage = None
        self._event_storage = None
        
        # Async storage component instances (created lazily)
        self._async_queue = None
        self._async_result_storage = None
        self._async_event_storage = None
        
        # Shared database connection
        self._conn: Optional[aiosqlite.Connection] = None
        self._conn_lock = anyio.Lock()
    
    async def initialize_async(self) -> None:
        """Initialize the backend asynchronously.
        
        Creates the database file and parent directories if needed.
        """
        if self._initialized:
            return
        
        async with self._init_lock:
            # Double-check pattern to prevent race conditions
            if self._initialized:
                return
            
            try:
                # Create parent directories if needed
                if self.create_dirs:
                    db_path = Path(self.db_path)
                    try:
                        db_path.parent.mkdir(parents=True, exist_ok=True)
                    except OSError as e:
                        logging.error(f"Failed to create directories for {db_path}: {e}")
                        raise
                
                # Initialize shared database connection
                await self._get_connection()
                
                # Initialize database schemas directly without creating temporary instances
                await self._initialize_schemas()
                
                self._initialized = True
            except (OSError, aiosqlite.Error, RuntimeError) as e:
                logging.error(f"Failed to initialize SQLite backend: {e}")
                raise
    
    async def _initialize_schemas(self) -> None:
        """Initialize database schemas for all components."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Initialize queue schema
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        queue_name TEXT NOT NULL,
                        func_name TEXT NOT NULL,
                        args_bytes BLOB NOT NULL,
                        kwargs_bytes BLOB NOT NULL,
                        created_at TEXT NOT NULL,
                        ttl_seconds INTEGER,
                        status TEXT NOT NULL DEFAULT 'pending',
                        locked_at TEXT,
                        lock_timeout_seconds INTEGER
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_queue_status
                    ON tasks(queue_name, status)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_locked_at
                    ON tasks(locked_at)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_created_at
                    ON tasks(created_at)
                """)
                
                # Initialize result storage schema
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
                
                # Initialize event storage schema
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
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_task_id_timestamp
                    ON events(task_id, timestamp)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_events_event_type_timestamp
                    ON events(event_type, timestamp)
                """)
                
                await db.commit()
            except aiosqlite.Error as e:
                await db.rollback()
                logging.error(f"Failed to initialize database schemas: {e}")
                raise
            except (aiosqlite.Error, RuntimeError) as e:
                await db.rollback()
                logging.error(f"Unexpected error during schema initialization: {e}")
                raise
    
    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a shared database connection, creating one if necessary."""
        if self._conn is None:
            async with self._conn_lock:
                # Double-check pattern to prevent race condition
                if self._conn is None:
                    try:
                        self._conn = await aiosqlite.connect(self.db_path)
                        await self._conn.execute("PRAGMA journal_mode=WAL;")
                    except aiosqlite.Error as e:
                        logging.error(f"Failed to create database connection: {e}")
                        raise
        return self._conn
    
    async def close_async(self) -> None:
        """Close the backend and clean up resources asynchronously."""
        # Close component connections
        if self._async_queue is not None:
            await self._async_queue.close()
        if self._async_result_storage is not None:
            await self._async_result_storage.close()
        if self._async_event_storage is not None:
            await self._async_event_storage.close()
        
        # Close shared database connection
        if self._conn is not None:
            async with self._conn_lock:
                if self._conn is not None:
                    try:
                        await self._conn.close()
                    except aiosqlite.Error as e:
                        logging.error(f"Failed to close database connection: {e}")
                    finally:
                        self._conn = None
        
        # Reset component instances
        self._queue = None
        self._result_storage = None
        self._event_storage = None
        self._async_queue = None
        self._async_result_storage = None
        self._async_event_storage = None
        self._initialized = False
    
    def create_queue(self) -> BaseQueue:
        """Create a task queue instance.
        
        Returns:
            A SQLiteQueue instance
        """
        if not self._queue:
            try:
                self.initialize()
                self._queue = SQLiteQueue(self.db_path)
            except Exception as e:
                logging.error(f"Failed to create queue instance: {e}")
                raise
        return self._queue
    
    def create_result_storage(self) -> BaseResultStorage:
        """Create a result storage instance.
        
        Returns:
            A SQLiteResultStorage instance
        """
        if not self._result_storage:
            try:
                self.initialize()
                self._result_storage = SQLiteResultStorage(self.db_path)
            except Exception as e:
                logging.error(f"Failed to create result storage instance: {e}")
                raise
        return self._result_storage
    
    def create_event_storage(self) -> BaseEventStorage:
        """Create an event storage instance.
        
        Returns:
            A SQLiteEventStorage instance
        """
        if not self._event_storage:
            try:
                self.initialize()
                self._event_storage = SQLiteEventStorage(self.db_path)
            except Exception as e:
                logging.error(f"Failed to create event storage instance: {e}")
                raise
        return self._event_storage
    
    def initialize(self) -> None:
        """Synchronous wrapper for initialize_async."""
        try:
            anyio.run(self.initialize_async)
        except (OSError, aiosqlite.Error, RuntimeError) as e:
            logging.error(f"Failed to initialize SQLite backend: {e}")
            raise
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        try:
            anyio.run(self.close_async)
        except (OSError, aiosqlite.Error, RuntimeError) as e:
            logging.error(f"Failed to close SQLite backend: {e}")
            raise
    
    # Additional utility methods
    
    async def create_async_queue(self) -> AsyncSQLiteQueue:
        """Create an async task queue instance.
        
        Returns:
            An AsyncSQLiteQueue instance
        """
        if not self._async_queue:
            await self.initialize_async()
            self._async_queue = AsyncSQLiteQueue(self.db_path)
        return self._async_queue
    
    async def create_async_result_storage(self) -> AsyncSQLiteResultStorage:
        """Create an async result storage instance.
        
        Returns:
            An AsyncSQLiteResultStorage instance
        """
        if not self._async_result_storage:
            await self.initialize_async()
            self._async_result_storage = AsyncSQLiteResultStorage(self.db_path)
        return self._async_result_storage
    
    async def create_async_event_storage(self) -> AsyncSQLiteEventStorage:
        """Create an async event storage instance.
        
        Returns:
            An AsyncSQLiteEventStorage instance
        """
        if not self._async_event_storage:
            await self.initialize_async()
            self._async_event_storage = AsyncSQLiteEventStorage(self.db_path)
        return self._async_event_storage
    
    async def cleanup_expired_results_async(self) -> int:
        """Convenience method to clean up expired results.
        
        Returns:
            Number of results cleaned up
        """
        result_storage = await self.create_async_result_storage()
        return await result_storage.cleanup_expired_async()
    
    def cleanup_expired_results(self) -> int:
        """Synchronous wrapper for cleanup_expired_results_async."""
        return anyio.run(self.cleanup_expired_results_async)
    
    async def get_database_stats_async(self) -> Dict[str, Any]:
        """Get database statistics asynchronously.
        
        Returns:
            Dictionary with database statistics
        """
        await self.initialize_async()
        
        stats = {}
        
        try:
            async with self._get_connection() as db:
                # Get table row counts
                for table in ["tasks", "results", "events"]:
                    try:
                        cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                        result = await cursor.fetchone()
                        stats[f"{table}_count"] = result[0] if result else 0
                    except aiosqlite.Error as e:
                        logging.error(f"Failed to get count for table {table}: {e}")
                        stats[f"{table}_count"] = 0
                
                # Get database file size
                try:
                    cursor = await db.execute("PRAGMA page_count")
                    page_count = await cursor.fetchone()
                    cursor = await db.execute("PRAGMA page_size")
                    page_size = await cursor.fetchone()
                    
                    if page_count and page_size:
                        stats["database_size_bytes"] = page_count[0] * page_size[0]
                except aiosqlite.Error as e:
                    logging.error(f"Failed to get database size: {e}")
                    stats["database_size_bytes"] = 0
                
                # Get queue statistics
                try:
                    cursor = await db.execute("""
                        SELECT queue_name, COUNT(*) as count, status
                        FROM tasks
                        GROUP BY queue_name, status
                    """)
                    queue_stats = {}
                    async for row in cursor:
                        queue_name, count, status = row
                        if queue_name not in queue_stats:
                            queue_stats[queue_name] = {}
                        queue_stats[queue_name][status] = count
                    stats["queue_stats"] = queue_stats
                except aiosqlite.Error as e:
                    logging.error(f"Failed to get queue statistics: {e}")
                    stats["queue_stats"] = {}
        except aiosqlite.Error as e:
            logging.error(f"Failed to get database stats: {e}")
            raise
        
        return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Synchronous wrapper for get_database_stats_async."""
        return anyio.run(self.get_database_stats_async)
    
    def __enter__(self):
        """Sync context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation of the backend."""
        return f"SQLiteBackend(db_path='{self.db_path}')"