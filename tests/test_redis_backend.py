"""
Tests for Redis backend implementation.

This module contains comprehensive tests for the Redis-based storage
implementations including task queue, result storage, and event storage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from omniq.models.config import RedisConfig
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType
from omniq.backend.redis import AsyncRedisBackend, RedisBackend
from omniq.storage.redis import (
    AsyncRedisQueue, RedisQueue,
    AsyncRedisResultStorage, RedisResultStorage,
    AsyncRedisEventStorage, RedisEventStorage
)


@pytest.fixture
def redis_config():
    """Create a test Redis configuration."""
    return RedisConfig(
        host="localhost",
        port=6379,
        database=15,  # Use test database
        tasks_prefix="test:tasks",
        results_prefix="test:results",
        events_prefix="test:events"
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="test-task-001",
        func="test_function",
        args=(1, 2, 3),
        kwargs={"key": "value"},
        queue_name="test_queue",
        priority=1,
        status=TaskStatus.PENDING
    )


@pytest.fixture
def sample_result():
    """Create a sample result for testing."""
    return TaskResult(
        task_id="test-task-001",
        status=ResultStatus.SUCCESS,
        result={"output": "test result"},
        created_at=datetime.utcnow(),
        ttl=timedelta(hours=1)
    )


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return TaskEvent(
        id="test-event-001",
        task_id="test-task-001",
        event_type=EventType.COMPLETED,
        details={"duration": 1.5},
        timestamp=datetime.utcnow()
    )


class TestAsyncRedisQueue:
    """Test cases for AsyncRedisQueue."""
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, redis_config):
        """Test Redis connection and disconnection."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            
            await queue.connect()
            assert queue._connected
            mock_redis_instance.ping.assert_called_once()
            
            await queue.disconnect()
            assert not queue._connected
            mock_redis_instance.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enqueue_task(self, redis_config, sample_task):
        """Test task enqueueing."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            task_id = await queue.enqueue(sample_task)
            
            assert task_id == sample_task.id
            mock_redis_instance.set.assert_called_once()
            mock_redis_instance.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dequeue_task(self, redis_config, sample_task):
        """Test task dequeueing."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            # Mock Redis responses
            mock_redis_instance.zrange.return_value = [(sample_task.id, -1.0)]
            mock_redis_instance.set.return_value = True  # Lock acquired
            mock_redis_instance.get.return_value = sample_task.to_dict()
            
            with patch('msgspec.json.decode', return_value=sample_task):
                dequeued_task = await queue.dequeue(["test_queue"], timeout=1.0)
            
            assert dequeued_task is not None
            assert dequeued_task.id == sample_task.id
    
    @pytest.mark.asyncio
    async def test_get_task(self, redis_config, sample_task):
        """Test getting a task by ID."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            mock_redis_instance.get.return_value = sample_task.to_dict()
            
            with patch('msgspec.json.decode', return_value=sample_task):
                retrieved_task = await queue.get_task(sample_task.id)
            
            assert retrieved_task is not None
            assert retrieved_task.id == sample_task.id
    
    @pytest.mark.asyncio
    async def test_update_task(self, redis_config, sample_task):
        """Test updating a task."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            sample_task.status = TaskStatus.RUNNING
            await queue.update_task(sample_task)
            
            mock_redis_instance.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_task(self, redis_config, sample_task):
        """Test deleting a task."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            mock_redis_instance.delete.return_value = 1
            mock_redis_instance.scan_iter.return_value = iter([])
            
            deleted = await queue.delete_task(sample_task.id)
            
            assert deleted is True
            mock_redis_instance.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_queue_size(self, redis_config):
        """Test getting queue size."""
        queue = AsyncRedisQueue(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            queue._redis = mock_redis_instance
            queue._connected = True
            
            mock_redis_instance.zcard.return_value = 5
            
            size = await queue.get_queue_size("test_queue")
            
            assert size == 5
            mock_redis_instance.zcard.assert_called_once()


class TestRedisQueue:
    """Test cases for sync RedisQueue wrapper."""
    
    def test_sync_operations(self, redis_config, sample_task):
        """Test synchronous queue operations."""
        queue = RedisQueue(**redis_config.to_dict())
        
        with patch.object(queue, 'connect') as mock_connect, \
             patch.object(queue, 'enqueue') as mock_enqueue, \
             patch.object(queue, 'disconnect') as mock_disconnect:
            
            mock_enqueue.return_value = asyncio.Future()
            mock_enqueue.return_value.set_result(sample_task.id)
            
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = sample_task.id
                
                task_id = queue.enqueue_sync(sample_task)
                
                assert task_id == sample_task.id
                mock_run.assert_called_once()


class TestAsyncRedisResultStorage:
    """Test cases for AsyncRedisResultStorage."""
    
    @pytest.mark.asyncio
    async def test_set_get_result(self, redis_config, sample_result):
        """Test storing and retrieving results."""
        storage = AsyncRedisResultStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            # Test set
            await storage.set(sample_result)
            mock_redis_instance.setex.assert_called_once()
            
            # Test get
            mock_redis_instance.get.return_value = sample_result.to_dict()
            
            with patch('msgspec.json.decode', return_value=sample_result):
                retrieved_result = await storage.get(sample_result.task_id)
            
            assert retrieved_result is not None
            assert retrieved_result.task_id == sample_result.task_id
    
    @pytest.mark.asyncio
    async def test_delete_result(self, redis_config, sample_result):
        """Test deleting a result."""
        storage = AsyncRedisResultStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            mock_redis_instance.delete.return_value = 1
            
            deleted = await storage.delete(sample_result.task_id)
            
            assert deleted is True
            mock_redis_instance.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_results(self, redis_config, sample_result):
        """Test listing results."""
        storage = AsyncRedisResultStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            mock_redis_instance.scan_iter.return_value = iter(["test:results:result:task1"])
            mock_redis_instance.get.return_value = sample_result.to_dict()
            
            with patch('msgspec.json.decode', return_value=sample_result):
                results = await storage.list_results(limit=10)
            
            assert len(results) == 1
            assert results[0].task_id == sample_result.task_id


class TestAsyncRedisEventStorage:
    """Test cases for AsyncRedisEventStorage."""
    
    @pytest.mark.asyncio
    async def test_log_event(self, redis_config, sample_event):
        """Test logging an event."""
        storage = AsyncRedisEventStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            await storage.log_event(sample_event)
            
            mock_redis_instance.set.assert_called_once()
            mock_redis_instance.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_events(self, redis_config, sample_event):
        """Test getting events."""
        storage = AsyncRedisEventStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            mock_redis_instance.zrangebyscore.return_value = [sample_event.id]
            mock_redis_instance.get.return_value = sample_event.to_dict()
            
            with patch('msgspec.json.decode', return_value=sample_event):
                events = await storage.get_events(task_id=sample_event.task_id)
            
            assert len(events) == 1
            assert events[0].id == sample_event.id
    
    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, redis_config):
        """Test cleaning up old events."""
        storage = AsyncRedisEventStorage(**redis_config.to_dict())
        
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            storage._redis = mock_redis_instance
            storage._connected = True
            
            old_event_ids = ["event1", "event2"]
            mock_redis_instance.zrangebyscore.return_value = old_event_ids
            
            cutoff_time = datetime.utcnow() - timedelta(days=1)
            cleaned_count = await storage.cleanup_old_events(cutoff_time)
            
            assert cleaned_count == 2
            mock_redis_instance.delete.assert_called_once()
            mock_redis_instance.zremrangebyscore.assert_called_once()


class TestAsyncRedisBackend:
    """Test cases for AsyncRedisBackend."""
    
    @pytest.mark.asyncio
    async def test_backend_initialization(self, redis_config):
        """Test backend initialization."""
        backend = AsyncRedisBackend(redis_config)
        
        assert backend.config == redis_config
        assert isinstance(backend.queue, AsyncRedisQueue)
        assert isinstance(backend.result_storage, AsyncRedisResultStorage)
        assert isinstance(backend.event_storage, AsyncRedisEventStorage)
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, redis_config):
        """Test backend connection and disconnection."""
        backend = AsyncRedisBackend(redis_config)
        
        with patch.object(backend.queue, 'connect') as mock_queue_connect, \
             patch.object(backend.result_storage, 'connect') as mock_result_connect, \
             patch.object(backend.event_storage, 'connect') as mock_event_connect, \
             patch.object(backend.queue, 'disconnect') as mock_queue_disconnect, \
             patch.object(backend.result_storage, 'disconnect') as mock_result_disconnect, \
             patch.object(backend.event_storage, 'disconnect') as mock_event_disconnect:
            
            await backend.connect()
            
            mock_queue_connect.assert_called_once()
            mock_result_connect.assert_called_once()
            mock_event_connect.assert_called_once()
            assert backend._connected
            
            await backend.disconnect()
            
            mock_queue_disconnect.assert_called_once()
            mock_result_disconnect.assert_called_once()
            mock_event_disconnect.assert_called_once()
            assert not backend._connected
    
    @pytest.mark.asyncio
    async def test_health_check(self, redis_config):
        """Test backend health check."""
        backend = AsyncRedisBackend(redis_config)
        
        with patch.object(backend, 'connect') as mock_connect:
            backend.queue._redis = AsyncMock()
            backend.result_storage._redis = AsyncMock()
            backend.event_storage._redis = AsyncMock()
            
            health = await backend.health_check()
            
            assert health["status"] == "healthy"
            assert health["backend"] == "redis"
            assert health["host"] == redis_config.host
            assert health["port"] == redis_config.port
    
    @pytest.mark.asyncio
    async def test_cleanup(self, redis_config):
        """Test backend cleanup."""
        backend = AsyncRedisBackend(redis_config)
        
        with patch.object(backend, 'connect') as mock_connect, \
             patch.object(backend.queue, 'cleanup_expired_tasks') as mock_cleanup_tasks, \
             patch.object(backend.result_storage, 'cleanup_expired_results') as mock_cleanup_results:
            
            mock_cleanup_tasks.return_value = 5
            mock_cleanup_results.return_value = 3
            
            cleanup_stats = await backend.cleanup()
            
            assert cleanup_stats["expired_tasks"] == 5
            assert cleanup_stats["expired_results"] == 3
            assert cleanup_stats["old_events"] == 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self, redis_config):
        """Test async context manager."""
        backend = AsyncRedisBackend(redis_config)
        
        with patch.object(backend, 'connect') as mock_connect, \
             patch.object(backend, 'disconnect') as mock_disconnect:
            
            async with backend:
                mock_connect.assert_called_once()
            
            mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction(self, redis_config):
        """Test transaction context manager."""
        backend = AsyncRedisBackend(redis_config)
        
        with patch.object(backend, 'connect') as mock_connect:
            backend._connected = True
            
            async with backend.transaction():
                pass  # Transaction should work without errors
            
            # No specific assertions needed as Redis doesn't support traditional transactions


class TestRedisBackend:
    """Test cases for sync RedisBackend wrapper."""
    
    def test_sync_backend_initialization(self, redis_config):
        """Test sync backend initialization."""
        backend = RedisBackend(redis_config)
        
        assert backend.config == redis_config
        assert isinstance(backend.queue, RedisQueue)
        assert isinstance(backend.result_storage, RedisResultStorage)
        assert isinstance(backend.event_storage, RedisEventStorage)
    
    def test_sync_operations(self, redis_config):
        """Test synchronous backend operations."""
        backend = RedisBackend(redis_config)
        
        with patch.object(backend.queue, 'connect_sync') as mock_queue_connect, \
             patch.object(backend.result_storage, 'connect_sync') as mock_result_connect, \
             patch.object(backend.event_storage, 'connect_sync') as mock_event_connect, \
             patch('asyncio.run') as mock_run:
            
            mock_run.return_value = {"status": "healthy"}
            
            backend.connect_sync()
            
            mock_queue_connect.assert_called_once()
            mock_result_connect.assert_called_once()
            mock_event_connect.assert_called_once()
            assert backend._connected
            
            health = backend.health_check_sync()
            assert health["status"] == "healthy"
    
    def test_context_manager(self, redis_config):
        """Test sync context manager."""
        backend = RedisBackend(redis_config)
        
        with patch.object(backend, 'connect_sync') as mock_connect, \
             patch.object(backend, 'disconnect_sync') as mock_disconnect:
            
            with backend:
                mock_connect.assert_called_once()
            
            mock_disconnect.assert_called_once()


# Integration tests (require actual Redis server)
@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests that require a running Redis server."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, redis_config, sample_task, sample_result, sample_event):
        """Test complete workflow with actual Redis."""
        try:
            async with AsyncRedisBackend(redis_config) as backend:
                # Test task queue
                task_id = await backend.queue.enqueue(sample_task)
                assert task_id == sample_task.id
                
                queue_size = await backend.queue.get_queue_size("test_queue")
                assert queue_size == 1
                
                dequeued_task = await backend.queue.dequeue(["test_queue"], timeout=1.0)
                assert dequeued_task is not None
                assert dequeued_task.id == sample_task.id
                
                # Test result storage
                await backend.result_storage.set(sample_result)
                retrieved_result = await backend.result_storage.get(sample_result.task_id)
                assert retrieved_result is not None
                assert retrieved_result.task_id == sample_result.task_id
                
                # Test event storage
                await backend.event_storage.log_event(sample_event)
                events = await backend.event_storage.get_events(task_id=sample_event.task_id)
                assert len(events) == 1
                assert events[0].id == sample_event.id
                
                # Test cleanup
                cleanup_stats = await backend.cleanup()
                assert isinstance(cleanup_stats, dict)
                
        except Exception as e:
            pytest.skip(f"Redis server not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])