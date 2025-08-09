"""SQLite backend implementation for OmniQ.

This module provides the SQLiteBackend class that acts as a factory
for creating SQLite-based storage component instances.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any

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
        
        # Storage component instances (created lazily)
        self._queue = None
        self._result_storage = None
        self._event_storage = None
    
    async def initialize_async(self) -> None:
        """Initialize the backend asynchronously.
        
        Creates the database file and parent directories if needed.
        """
        if self._initialized:
            return
        
        # Create parent directories if needed
        if self.create_dirs:
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize all storage components to ensure schema creation
        # We create temporary instances just to trigger schema initialization
        temp_queue = AsyncSQLiteQueue(self.db_path)
        temp_result_storage = AsyncSQLiteResultStorage(self.db_path)
        temp_event_storage = AsyncSQLiteEventStorage(self.db_path)
        
        await temp_queue._ensure_initialized()
        await temp_result_storage._ensure_initialized()
        await temp_event_storage._ensure_initialized()
        
        self._initialized = True
    
    async def close_async(self) -> None:
        """Close the backend and clean up resources asynchronously.
        
        Note: SQLite doesn't require explicit connection cleanup in our implementation
        since we use connection-per-operation pattern.
        """
        # Reset component instances
        self._queue = None
        self._result_storage = None
        self._event_storage = None
        self._initialized = False
    
    def create_queue(self) -> BaseQueue:
        """Create a task queue instance.
        
        Returns:
            A SQLiteQueue instance
        """
        if not self._queue:
            self._queue = SQLiteQueue(self.db_path)
        return self._queue
    
    def create_result_storage(self) -> BaseResultStorage:
        """Create a result storage instance.
        
        Returns:
            A SQLiteResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = SQLiteResultStorage(self.db_path)
        return self._result_storage
    
    def create_event_storage(self) -> BaseEventStorage:
        """Create an event storage instance.
        
        Returns:
            A SQLiteEventStorage instance
        """
        if not self._event_storage:
            self._event_storage = SQLiteEventStorage(self.db_path)
        return self._event_storage
    
    def initialize(self) -> None:
        """Synchronous wrapper for initialize_async."""
        anyio.run(self.initialize_async)
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        anyio.run(self.close_async)
    
    # Additional utility methods
    
    async def create_async_queue(self) -> AsyncSQLiteQueue:
        """Create an async task queue instance.
        
        Returns:
            An AsyncSQLiteQueue instance
        """
        return AsyncSQLiteQueue(self.db_path)
    
    async def create_async_result_storage(self) -> AsyncSQLiteResultStorage:
        """Create an async result storage instance.
        
        Returns:
            An AsyncSQLiteResultStorage instance
        """
        return AsyncSQLiteResultStorage(self.db_path)
    
    async def create_async_event_storage(self) -> AsyncSQLiteEventStorage:
        """Create an async event storage instance.
        
        Returns:
            An AsyncSQLiteEventStorage instance
        """
        return AsyncSQLiteEventStorage(self.db_path)
    
    async def cleanup_expired_results_async(self) -> int:
        """Convenience method to clean up expired results.
        
        Returns:
            Number of results cleaned up
        """
        result_storage = AsyncSQLiteResultStorage(self.db_path)
        return await result_storage.cleanup_expired_async()
    
    def cleanup_expired_results(self) -> int:
        """Synchronous wrapper for cleanup_expired_results_async."""
        return anyio.run(self.cleanup_expired_results_async)
    
    async def get_database_stats_async(self) -> Dict[str, Any]:
        """Get database statistics asynchronously.
        
        Returns:
            Dictionary with database statistics
        """
        import aiosqlite
        
        stats = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get table row counts
            for table in ["tasks", "results", "events"]:
                try:
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                    result = await cursor.fetchone()
                    stats[f"{table}_count"] = result[0] if result else 0
                except Exception:
                    stats[f"{table}_count"] = 0
            
            # Get database file size
            try:
                cursor = await db.execute("PRAGMA page_count")
                page_count = await cursor.fetchone()
                cursor = await db.execute("PRAGMA page_size")
                page_size = await cursor.fetchone()
                
                if page_count and page_size:
                    stats["database_size_bytes"] = page_count[0] * page_size[0]
            except Exception:
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
            except Exception:
                stats["queue_stats"] = {}
        
        return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Synchronous wrapper for get_database_stats_async."""
        return anyio.run(self.get_database_stats_async)
    
    def __repr__(self) -> str:
        """String representation of the backend."""
        return f"SQLiteBackend(db_path='{self.db_path}')"