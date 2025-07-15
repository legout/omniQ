"""
PostgreSQL backend implementation for OmniQ.

This module provides a unified PostgreSQL backend that combines all storage
components (task queue, result storage, event storage, and schedule storage)
into a single, cohesive interface.
"""

from typing import Optional, Dict, Any
from ..models.config import PostgresConfig
from ..storage.postgres import (
    AsyncPostgresQueue,
    PostgresQueue,
    AsyncPostgresResultStorage,
    PostgresResultStorage,
    AsyncPostgresEventStorage,
    PostgresEventStorage,
    AsyncPostgresScheduleStorage,
    PostgresScheduleStorage,
)


class AsyncPostgreSQLBackend:
    """
    Async PostgreSQL backend for OmniQ.
    
    This class provides a unified interface to all PostgreSQL storage components,
    managing connections and providing a single entry point for all storage operations.
    """
    
    def __init__(self, config: PostgresConfig):
        """
        Initialize the PostgreSQL backend.
        
        Args:
            config: PostgreSQL configuration object
        """
        self.config = config
        
        # Initialize storage components
        storage_kwargs = {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "password": config.password,
            "min_connections": config.min_connections,
            "max_connections": config.max_connections,
            "command_timeout": config.command_timeout,
            "schema": config.schema,
        }
        
        # Task queue storage
        self.task_queue = AsyncPostgresQueue(
            tasks_table=config.tasks_table,
            **storage_kwargs
        )
        
        # Result storage
        self.result_storage = AsyncPostgresResultStorage(
            results_table=config.results_table,
            **storage_kwargs
        )
        
        # Event storage
        self.event_storage = AsyncPostgresEventStorage(
            events_table=config.events_table,
            **storage_kwargs
        )
        
        # Schedule storage
        self.schedule_storage = AsyncPostgresScheduleStorage(
            schedules_table=config.schedules_table,
            **storage_kwargs
        )
    
    async def connect(self) -> None:
        """Connect all storage components."""
        await self.task_queue.connect()
        await self.result_storage.connect()
        await self.event_storage.connect()
        await self.schedule_storage.connect()
    
    async def disconnect(self) -> None:
        """Disconnect all storage components."""
        await self.task_queue.disconnect()
        await self.result_storage.disconnect()
        await self.event_storage.disconnect()
        await self.schedule_storage.disconnect()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class PostgreSQLBackend:
    """
    Synchronous PostgreSQL backend for OmniQ.
    
    This class provides a unified synchronous interface to all PostgreSQL storage
    components, managing connections and providing a single entry point for all
    storage operations.
    """
    
    def __init__(self, config: PostgresConfig):
        """
        Initialize the PostgreSQL backend.
        
        Args:
            config: PostgreSQL configuration object
        """
        self.config = config
        
        # Initialize storage components
        storage_kwargs = {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "password": config.password,
            "min_connections": config.min_connections,
            "max_connections": config.max_connections,
            "command_timeout": config.command_timeout,
            "schema": config.schema,
        }
        
        # Task queue storage
        self.task_queue = PostgresQueue(
            tasks_table=config.tasks_table,
            **storage_kwargs
        )
        
        # Result storage
        self.result_storage = PostgresResultStorage(
            results_table=config.results_table,
            **storage_kwargs
        )
        
        # Event storage
        self.event_storage = PostgresEventStorage(
            events_table=config.events_table,
            **storage_kwargs
        )
        
        # Schedule storage
        self.schedule_storage = PostgresScheduleStorage(
            schedules_table=config.schedules_table,
            **storage_kwargs
        )
    
    def connect(self) -> None:
        """Connect all storage components."""
        self.task_queue.connect_sync()
        self.result_storage.connect_sync()
        self.event_storage.connect_sync()
        self.schedule_storage.connect_sync()
    
    def disconnect(self) -> None:
        """Disconnect all storage components."""
        self.task_queue.disconnect_sync()
        self.result_storage.disconnect_sync()
        self.event_storage.disconnect_sync()
        self.schedule_storage.disconnect_sync()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect()


# Convenience functions for creating backends
def create_postgres_backend(
    host: str = "localhost",
    port: int = 5432,
    database: str = "omniq",
    username: str = "postgres",
    password: str = "",
    **kwargs
) -> PostgreSQLBackend:
    """
    Create a PostgreSQL backend with the given configuration.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        username: Username
        password: Password
        **kwargs: Additional configuration options
    
    Returns:
        Configured PostgreSQL backend
    """
    config = PostgresConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        **kwargs
    )
    return PostgreSQLBackend(config)


def create_async_postgres_backend(
    host: str = "localhost",
    port: int = 5432,
    database: str = "omniq",
    username: str = "postgres",
    password: str = "",
    **kwargs
) -> AsyncPostgreSQLBackend:
    """
    Create an async PostgreSQL backend with the given configuration.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        username: Username
        password: Password
        **kwargs: Additional configuration options
    
    Returns:
        Configured async PostgreSQL backend
    """
    config = PostgresConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        **kwargs
    )
    return AsyncPostgreSQLBackend(config)