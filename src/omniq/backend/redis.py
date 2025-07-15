"""
Redis backend implementation for OmniQ.

This module provides a unified Redis backend that combines task queue,
result storage, and event storage using Redis as the underlying storage engine.
"""

from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from ..storage.redis import (
    AsyncRedisQueue, RedisQueue,
    AsyncRedisResultStorage, RedisResultStorage,
    AsyncRedisEventStorage, RedisEventStorage
)
from ..models.config import RedisConfig


class AsyncRedisBackend:
    """
    Async Redis backend implementation.
    
    This class provides a unified interface to Redis-based storage
    components for OmniQ, including task queue, result storage,
    and event storage.
    """
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis backend.
        
        Args:
            config: Redis configuration
        """
        self.config = config
        
        # Initialize storage components with shared Redis config
        redis_kwargs = {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "password": config.password,
            "max_connections": config.max_connections,
            "socket_timeout": config.socket_timeout,
            "socket_connect_timeout": config.socket_connect_timeout,
            "retry_on_timeout": config.retry_on_timeout,
        }
        
        # Add SSL settings if configured
        if config.ssl:
            redis_kwargs.update({
                "ssl": config.ssl,
                "ssl_cert_reqs": config.ssl_cert_reqs,
                "ssl_ca_certs": config.ssl_ca_certs,
                "ssl_certfile": config.ssl_certfile,
                "ssl_keyfile": config.ssl_keyfile,
            })
        
        self.queue = AsyncRedisQueue(
            tasks_prefix=config.tasks_prefix,
            **redis_kwargs
        )
        
        self.result_storage = AsyncRedisResultStorage(
            results_prefix=config.results_prefix,
            **redis_kwargs
        )
        
        self.event_storage = AsyncRedisEventStorage(
            events_prefix=config.events_prefix,
            **redis_kwargs
        )
        
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Redis backend."""
        if self._connected:
            return
        
        await self.queue.connect()
        await self.result_storage.connect()
        await self.event_storage.connect()
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from Redis backend."""
        if not self._connected:
            return
        
        await self.queue.disconnect()
        await self.result_storage.disconnect()
        await self.event_storage.disconnect()
        
        self._connected = False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis backend.
        
        Returns:
            Health check results
        """
        try:
            if not self._connected:
                await self.connect()
            
            # Test basic Redis operations
            if self.queue._redis:
                await self.queue._redis.ping()
            if self.result_storage._redis:
                await self.result_storage._redis.ping()
            if self.event_storage._redis:
                await self.event_storage._redis.ping()
            
            return {
                "status": "healthy",
                "backend": "redis",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "connected": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "connected": False,
                "error": str(e)
            }
    
    async def cleanup(self) -> Dict[str, int]:
        """
        Perform cleanup operations on Redis backend.
        
        Returns:
            Cleanup statistics
        """
        if not self._connected:
            await self.connect()
        
        # Cleanup expired tasks
        expired_tasks = await self.queue.cleanup_expired_tasks()
        
        # Cleanup expired results
        expired_results = await self.result_storage.cleanup_expired_results()
        
        return {
            "expired_tasks": expired_tasks,
            "expired_results": expired_results,
            "old_events": 0  # Event cleanup requires a cutoff time
        }
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for Redis transactions.
        
        Note: Redis doesn't support traditional ACID transactions,
        but this provides a consistent interface with other backends.
        """
        if not self._connected:
            await self.connect()
        
        try:
            yield self
        except Exception:
            # Redis operations are atomic by nature
            # No rollback needed
            raise
    
    # Async context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class RedisBackend(AsyncRedisBackend):
    """
    Synchronous wrapper around AsyncRedisBackend.
    
    This class provides a synchronous interface to the async Redis backend
    implementation using asyncio for thread-safe execution.
    """
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis backend.
        
        Args:
            config: Redis configuration
        """
        super().__init__(config)
        
        # Create sync wrappers for storage components
        redis_kwargs = {}
        if config.ssl:
            redis_kwargs.update({
                "ssl": config.ssl,
                "ssl_cert_reqs": config.ssl_cert_reqs,
                "ssl_ca_certs": config.ssl_ca_certs,
                "ssl_certfile": config.ssl_certfile,
                "ssl_keyfile": config.ssl_keyfile,
            })
        
        self.queue = RedisQueue(
            host=config.host,
            port=config.port,
            database=config.database,
            password=config.password,
            tasks_prefix=config.tasks_prefix,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            retry_on_timeout=config.retry_on_timeout,
            **redis_kwargs
        )
        
        self.result_storage = RedisResultStorage(
            host=config.host,
            port=config.port,
            database=config.database,
            password=config.password,
            results_prefix=config.results_prefix,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            retry_on_timeout=config.retry_on_timeout,
            **redis_kwargs
        )
        
        self.event_storage = RedisEventStorage(
            host=config.host,
            port=config.port,
            database=config.database,
            password=config.password,
            events_prefix=config.events_prefix,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            retry_on_timeout=config.retry_on_timeout,
            **redis_kwargs
        )
    
    def connect_sync(self) -> None:
        """Connect to Redis backend (sync)."""
        self.queue.connect_sync()
        self.result_storage.connect_sync()
        self.event_storage.connect_sync()
        self._connected = True
    
    def disconnect_sync(self) -> None:
        """Disconnect from Redis backend (sync)."""
        if not self._connected:
            return
        
        self.queue.disconnect_sync()
        self.result_storage.disconnect_sync()
        self.event_storage.disconnect_sync()
        self._connected = False
    
    def health_check_sync(self) -> Dict[str, Any]:
        """Perform health check on Redis backend (sync)."""
        import asyncio
        return asyncio.run(self.health_check())
    
    def cleanup_sync(self) -> Dict[str, int]:
        """Perform cleanup operations on Redis backend (sync)."""
        import asyncio
        return asyncio.run(self.cleanup())
    
    # Sync context manager support
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


# Factory function for creating Redis backends
def create_redis_backend(config: RedisConfig, async_mode: bool = False):
    """
    Create a Redis backend instance.
    
    Args:
        config: Redis configuration
        async_mode: Whether to create async or sync backend
        
    Returns:
        Redis backend instance
    """
    if async_mode:
        return AsyncRedisBackend(config)
    else:
        return RedisBackend(config)