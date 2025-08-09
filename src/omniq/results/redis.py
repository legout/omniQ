"""Redis result storage implementations for OmniQ.

This module provides concrete Redis-based implementations of the result storage interface:
- AsyncRedisResultStorage and RedisResultStorage: Result storage with TTL support using redis.asyncio

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import anyio
import redis.asyncio as redis
import msgspec

from .base import BaseResultStorage
from ..models.result import TaskResult, TaskStatus


class AsyncRedisResultStorage(BaseResultStorage):
    """Async Redis-based result storage implementation.
    
    Features:
    - TTL support with automatic cleanup
    - Status-based querying
    - Fast in-memory operations with Redis
    - Connection pooling for efficiency
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "omniq",
        max_connections: int = 10,
        **connection_kwargs
    ):
        """Initialize the async Redis result storage.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
            max_connections: Maximum number of connections in the pool
            **connection_kwargs: Additional connection arguments for redis
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        self.connection_kwargs = connection_kwargs
        self.redis: Optional[redis.Redis] = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the Redis connection is initialized."""
        if self._initialized:
            return
        
        # Create Redis connection pool
        self.redis = redis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            **self.connection_kwargs
        )
        self.redis = redis.Redis(connection_pool=self.redis)
        
        # Test connection
        await self.redis.ping()
        
        self._initialized = True
    
    def _get_result_key(self, task_id: uuid.UUID) -> str:
        """Get the Redis key for a specific result."""
        return f"{self.key_prefix}:result:{task_id}"
    
    def _get_status_set_key(self, status: str) -> str:
        """Get the Redis key for a status set."""
        return f"{self.key_prefix}:status:{status}"
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        # Serialize result data
        result_data = {
            "task_id": str(result.task_id),
            "status": result.status.value,
            "result_data": msgspec.json.encode(result.result_data),
            "timestamp": result.timestamp.isoformat(),
            "ttl_seconds": int(result.ttl.total_seconds()) if result.ttl else None
        }
        
        # Calculate expiration time
        expiration = None
        if result.ttl:
            expiration = int(result.ttl.total_seconds())
        
        # Use a pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            # Store result data
            result_key = self._get_result_key(result.task_id)
            if expiration:
                await pipe.setex(result_key, expiration, json.dumps(result_data))
            else:
                await pipe.set(result_key, json.dumps(result_data))
            
            # Add result to status set
            status_set_key = self._get_status_set_key(result.status.value)
            await pipe.sadd(status_set_key, str(result.task_id))
            
            # Execute pipeline
            await pipe.execute()
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        result_key = self._get_result_key(task_id)
        result_data_json = await self.redis.get(result_key)
        
        if not result_data_json:
            return None
        
        result_data = json.loads(result_data_json)
        
        # Reconstruct the result
        result_data_decoded = msgspec.json.decode(result_data["result_data"]) if result_data["result_data"] else None
        timestamp = datetime.fromisoformat(result_data["timestamp"])
        status = TaskStatus(result_data["status"])
        
        # Calculate TTL
        ttl = None
        if result_data["ttl_seconds"]:
            ttl = timedelta(seconds=result_data["ttl_seconds"])
        
        return TaskResult(
            task_id=task_id,
            status=status,
            result_data=result_data_decoded,
            timestamp=timestamp,
            ttl=ttl
        )
    
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously."""
        await self._ensure_initialized()
        
        # Get result data first to determine status
        result_key = self._get_result_key(task_id)
        result_data_json = await self.redis.get(result_key)
        
        if not result_data_json:
            return False
        
        result_data = json.loads(result_data_json)
        status = result_data["status"]
        
        # Use a pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            # Delete result data
            await pipe.delete(result_key)
            
            # Remove from status set
            status_set_key = self._get_status_set_key(status)
            await pipe.srem(status_set_key, str(task_id))
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Check if result was deleted
            return results[0] == 1
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously.
        
        Note: Redis automatically expires keys with TTL, so this is mainly
        for cleanup of results without explicit TTL or for status sets.
        """
        await self._ensure_initialized()
        
        # This is handled automatically by Redis TTL
        # We'll just clean up any orphaned status set entries
        count = 0
        
        # Get all status sets
        status_keys = await self.redis.keys(f"{self.key_prefix}:status:*")
        
        for status_key in status_keys:
            # Get all task IDs in this status set
            task_ids = await self.redis.smembers(status_key)
            
            for task_id_str in task_ids:
                task_id = uuid.UUID(task_id_str.decode())
                result_key = self._get_result_key(task_id)
                
                # Check if result still exists
                if not await self.redis.exists(result_key):
                    # Remove from status set
                    await self.redis.srem(status_key, task_id_str)
                    count += 1
        
        return count
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        status_set_key = self._get_status_set_key(status)
        task_ids = await self.redis.smembers(status_set_key)
        
        for task_id_str in task_ids:
            task_id = uuid.UUID(task_id_str.decode())
            result = await self.get_result_async(task_id)
            
            if result:
                yield result
    
    async def close_async(self) -> None:
        """Close the Redis connection pool."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._initialized = False


class RedisResultStorage(AsyncRedisResultStorage):
    """Synchronous wrapper for AsyncRedisResultStorage."""
    
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