"""PostgreSQL backend integration for OmniQ.

This module provides the PostgreSQL backend implementation that combines
the PostgreSQL queue, result storage, and event storage components.
"""

from typing import Dict, Any, Optional

from .base import BaseBackend
from ..queue.postgres import AsyncPostgresQueue, PostgresQueue
from ..results.postgres import AsyncPostgresResultStorage, PostgresResultStorage
from ..events.postgres import AsyncPostgresEventStorage, PostgresEventStorage


class PostgresBackend(BaseBackend):
    """PostgreSQL backend for OmniQ.
    
    This backend uses PostgreSQL for all storage components:
    - Task queue: PostgreSQL with row-level locking
    - Result storage: PostgreSQL with TTL support
    - Event storage: PostgreSQL with time-based querying
    """
    
    def __init__(
        self,
        dsn: str,
        queue_table_name: str = "omniq_tasks",
        result_table_name: str = "omniq_results",
        event_table_name: str = "omniq_events",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the PostgreSQL backend.
        
        Args:
            dsn: PostgreSQL connection string
            queue_table_name: Name of the tasks table
            result_table_name: Name of the results table
            event_table_name: Name of the events table
            max_connections: Maximum number of connections in the pool
            **connection_kwargs: Additional connection arguments for asyncpg
        """
        config = {
            "dsn": dsn,
            "queue_table_name": queue_table_name,
            "result_table_name": result_table_name,
            "event_table_name": event_table_name,
            "max_connections": max_connections,
            "connection_kwargs": connection_kwargs
        }
        super().__init__(config)
        
        self.dsn = dsn
        self.queue_table_name = queue_table_name
        self.result_table_name = result_table_name
        self.event_table_name = event_table_name
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs
        
        self._queue: Optional[PostgresQueue] = None
        self._result_storage: Optional[PostgresResultStorage] = None
        self._event_storage: Optional[PostgresEventStorage] = None
    
    def create_queue(self) -> PostgresQueue:
        """Create a PostgreSQL task queue instance.
        
        Returns:
            A PostgresQueue instance
        """
        if not self._queue:
            self._queue = PostgresQueue(
                dsn=self.dsn,
                table_name=self.queue_table_name,
                max_connections=self.max_connections,
                **self.connection_kwargs
            )
        return self._queue
    
    def create_result_storage(self) -> PostgresResultStorage:
        """Create a PostgreSQL result storage instance.
        
        Returns:
            A PostgresResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = PostgresResultStorage(
                dsn=self.dsn,
                table_name=self.result_table_name,
                max_connections=self.max_connections,
                **self.connection_kwargs
            )
        return self._result_storage
    
    def create_event_storage(self) -> PostgresEventStorage:
        """Create a PostgreSQL event storage instance.
        
        Returns:
            A PostgresEventStorage instance
        """
        if not self._event_storage:
            self._event_storage = PostgresEventStorage(
                dsn=self.dsn,
                table_name=self.event_table_name,
                max_connections=self.max_connections,
                **self.connection_kwargs
            )
        return self._event_storage
    
    def close(self) -> None:
        """Close all backend components."""
        if self._queue:
            self._queue.close()
            self._queue = None
        
        if self._result_storage:
            self._result_storage.close()
            self._result_storage = None
        
        if self._event_storage:
            self._event_storage.close()
            self._event_storage = None
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()