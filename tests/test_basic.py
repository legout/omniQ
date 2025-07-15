"""
Basic tests for OmniQ functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from omniq import OmniQ, Task, TaskResult, TaskEvent
from omniq.models.task import TaskStatus
from omniq.models.event import EventType


@pytest.fixture
async def omniq():
    """Create an OmniQ instance for testing."""
    omniq = OmniQ()
    await omniq.connect()
    yield omniq
    await omniq.disconnect()


@pytest.fixture
def omniq_sync():
    """Create a sync OmniQ instance for testing."""
    omniq = OmniQ()
    omniq.connect_sync()
    yield omniq
    omniq.disconnect_sync()


class TestOmniQBasic:
    """Basic OmniQ functionality tests."""
    
    @pytest.mark.asyncio
    async def test_connection(self, omniq):
        """Test OmniQ connection."""
        assert omniq._task_queue is not None
        assert omniq._result_storage is not None
        assert omniq._event_storage is not None
    
    @pytest.mark.asyncio
    async def test_task_submission(self, omniq):
        """Test basic task submission."""
        task_id = await omniq.submit_task(
            func_name="test_function",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            queue="test_queue",
            priority=5
        )
        
        assert isinstance(task_id, str)
        assert len(task_id) > 0
        
        # Retrieve the task
        task = await omniq.get_task(task_id)
        assert task is not None
        assert task.func == "test_function"
        assert task.args == (1, 2, 3)
        assert task.kwargs == {"key": "value"}
        assert task.queue_name == "test_queue"
        assert task.priority == 5
        assert task.status == TaskStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_task_with_delay(self, omniq):
        """Test task submission with delay."""
        delay = timedelta(seconds=10)
        task_id = await omniq.submit_task(
            func_name="delayed_function",
            delay=delay
        )
        
        task = await omniq.get_task(task_id)
        assert task is not None
        assert task.run_at is not None
        assert task.run_at > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_task_with_ttl(self, omniq):
        """Test task submission with TTL."""
        ttl = timedelta(minutes=30)
        task_id = await omniq.submit_task(
            func_name="ttl_function",
            ttl=ttl
        )
        
        task = await omniq.get_task(task_id)
        assert task is not None
        assert task.ttl == ttl
        assert task.expires_at is not None
        assert task.expires_at > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_task_events(self, omniq):
        """Test task event logging."""
        task_id = await omniq.submit_task(
            func_name="event_test_function",
            queue="event_queue"
        )
        
        # Get events for the task
        events = await omniq.get_task_events(task_id)
        assert len(events) >= 1
        
        # Check the enqueued event
        enqueued_event = events[0]
        assert enqueued_event.task_id == task_id
        assert enqueued_event.event_type == EventType.ENQUEUED
        assert enqueued_event.queue_name == "event_queue"
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_queue(self, omniq):
        """Test listing tasks by queue."""
        # Submit multiple tasks to the same queue
        queue_name = "list_test_queue"
        task_ids = []
        
        for i in range(3):
            task_id = await omniq.submit_task(
                func_name=f"list_function_{i}",
                queue=queue_name
            )
            task_ids.append(task_id)
        
        # List tasks in the queue
        tasks = await omniq.get_tasks_by_queue(queue_name)
        assert len(tasks) >= 3
        
        # Check that our tasks are in the list
        retrieved_task_ids = [task.id for task in tasks]
        for task_id in task_ids:
            assert task_id in retrieved_task_ids
    
    def test_sync_operations(self, omniq_sync):
        """Test synchronous operations."""
        # Submit task synchronously
        task_id = omniq_sync.submit_task_sync(
            func_name="sync_function",
            args=(10, 20),
            queue="sync_queue"
        )
        
        assert isinstance(task_id, str)
        
        # Get task synchronously
        task = omniq_sync.get_task_sync(task_id)
        assert task is not None
        assert task.func == "sync_function"
        assert task.args == (10, 20)
        assert task.queue_name == "sync_queue"
    
    @pytest.mark.asyncio
    async def test_task_decorator(self, omniq):
        """Test task decorator functionality."""
        # Register a task using decorator
        @omniq.task(name="decorated_task", queue="decorator_queue", priority=3)
        def my_decorated_task(x: int, y: int) -> int:
            return x + y
        
        # Check that the task is registered
        registered_tasks = omniq.list_registered_tasks()
        assert "decorated_task" in registered_tasks
        
        # Check that we can get the registered function
        func = omniq.get_registered_task("decorated_task")
        assert func is not None
        assert func == my_decorated_task
        
        # Check that the function has the expected attributes
        assert hasattr(my_decorated_task, 'task_name')
        assert my_decorated_task.task_name == "decorated_task"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager functionality."""
        async with OmniQ() as omniq:
            # Should be connected
            assert omniq._task_queue is not None
            
            # Should be able to submit tasks
            task_id = await omniq.submit_task(
                func_name="context_test",
                queue="context_queue"
            )
            assert isinstance(task_id, str)
        
        # After exiting context, should be disconnected
        # (We can't easily test this without accessing private attributes)
    
    def test_sync_context_manager(self):
        """Test synchronous context manager functionality."""
        with OmniQ() as omniq:
            # Should be connected
            assert omniq._task_queue is not None
            
            # Should be able to submit tasks
            task_id = omniq.submit_task_sync(
                func_name="sync_context_test",
                queue="sync_context_queue"
            )
            assert isinstance(task_id, str)


class TestTaskModel:
    """Test Task model functionality."""
    
    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(
            func="test_function",
            args=(1, 2),
            kwargs={"key": "value"},
            queue_name="test_queue",
            priority=5
        )
        
        assert task.func == "test_function"
        assert task.args == (1, 2)
        assert task.kwargs == {"key": "value"}
        assert task.queue_name == "test_queue"
        assert task.priority == 5
        assert task.status == TaskStatus.PENDING
        assert isinstance(task.id, str)
        assert len(task.id) > 0
    
    def test_task_expiration(self):
        """Test task expiration logic."""
        # Task without TTL should not be expired
        task = Task(func="test_function")
        assert not task.is_expired()
        
        # Task with future expiration should not be expired
        task_future = Task(
            func="test_function",
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        assert not task_future.is_expired()
        
        # Task with past expiration should be expired
        task_past = Task(
            func="test_function",
            expires_at=datetime.utcnow() - timedelta(minutes=10)
        )
        assert task_past.is_expired()
    
    def test_task_ready_to_run(self):
        """Test task ready-to-run logic."""
        # Basic pending task should be ready
        task = Task(func="test_function")
        assert task.is_ready_to_run()
        
        # Completed task should not be ready
        task_completed = Task(func="test_function", status=TaskStatus.COMPLETED)
        assert not task_completed.is_ready_to_run()
        
        # Expired task should not be ready
        task_expired = Task(
            func="test_function",
            expires_at=datetime.utcnow() - timedelta(minutes=10)
        )
        assert not task_expired.is_ready_to_run()
        
        # Future scheduled task should not be ready
        task_future = Task(
            func="test_function",
            run_at=datetime.utcnow() + timedelta(minutes=10)
        )
        assert not task_future.is_ready_to_run()
    
    def test_task_retry_logic(self):
        """Test task retry logic."""
        task = Task(
            func="test_function",
            status=TaskStatus.FAILED,
            retry_count=1,
            max_retries=3
        )
        
        # Should be able to retry
        assert task.should_retry()
        
        # Exceeded max retries
        task.retry_count = 3
        assert not task.should_retry()
        
        # Not failed status
        task.status = TaskStatus.PENDING
        task.retry_count = 1
        assert not task.should_retry()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])