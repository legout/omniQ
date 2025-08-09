"""Redis backend integration for OmniQ.

This module provides the Redis backend implementation that combines
the Redis queue and result storage components.
"""

from typing import Dict, Any, Optional

from .base import BaseBackend
from ..queue.redis import AsyncRedisQueue, RedisQueue
from ..results.redis import AsyncRedisResultStorage, RedisResultStorage


class RedisBackend(BaseBackend):
    """Redis backend for OmniQ.
    
    This backend uses Redis for all storage components:
    - Task queue: Redis with atomic operations for locking
    - Result storage: Redis with TTL support
    - Event storage: Not supported with Redis backend
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "omniq",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the Redis backend.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
            max_connections: Maximum number of connections in the pool
            **connection_kwargs: Additional connection arguments for redis
        """
        config = {
            "redis_url": redis_url,
            "key_prefix": key_prefix,
            "max_connections": max_connections,
            "connection_kwargs": connection_kwargs
        }
        super().__init__(config)
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs
        
        self._queue: Optional[RedisQueue] = None
        self._result_storage: Optional[RedisResultStorage] = None
    
    def create_queue(self) -> RedisQueue:
        """Create a Redis task queue instance.
        
        Returns:
            A RedisQueue instance
        """
        if not self._queue:
            self._queue = RedisQueue(
                redis_url=self.redis_url,
                key_prefix=self.key_prefix,
                max_connections=self.max_connections,
                **self.connection_kwargs
            )
        return self._queue
    
    def create_result_storage(self) -> RedisResultStorage:
        """Create a Redis result storage instance.
        
        Returns:
            A RedisResultStorage instance
        """
        if not self._result_storage:
            self._result_storage = RedisResultStorage(
                redis_url=self.redis_url,
                key_prefix=self.key_prefix,
                max_connections=self.max_connections,
                **self.connection_kwargs
            )
        return self._result_storage
    
    def create_event_storage(self):
        """Create an event storage instance.
        
        Note: Redis backend does not support event storage.
        
        Returns:
            None
            
        Raises:
            NotImplementedError: Always raised as Redis doesn't support event storage
        """
        raise NotImplementedError("Redis backend does not support event storage")
    
    def close(self) -> None:
        """Close all backend components."""
        if self._queue:
            self._queue.close()
            self._queue = None
        
        if self._result_storage:
            self._result_storage.close()
            self._result_storage = None
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()